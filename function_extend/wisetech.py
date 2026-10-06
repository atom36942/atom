"""WiseTech buyer calculations. Functions are registered on app.state by Atom."""
import asyncio
import re
from datetime import date
from decimal import Decimal, InvalidOperation
import httpx
from fastapi import HTTPException


async def func_wisetech_request(*, app_state, endpoint, params=None, body=None, method="GET"):
    base_url = getattr(app_state, "config_wisetech_base_url", None)
    api_key = getattr(app_state, "config_wisetech_api_key", None)
    if not base_url or not api_key:
        raise HTTPException(503, "WiseTech is not configured.")
    try:
        response = await app_state.client_http.request(method,
            f"{base_url.rstrip('/')}/trade-service/api/v1/{endpoint}",
            headers={"X-Api-Key": api_key, "Accept": "application/json"},
            params=params, json=body, timeout=30.0, follow_redirects=False)
        if response.status_code in (401, 403):
            raise HTTPException(502, "WiseTech credentials were rejected. Contact the MGH integration team.")
        if not response.is_success:
            raise HTTPException(502, f"WiseTech request failed (HTTP {response.status_code}).")
        return response.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "WiseTech request timed out.") from None
    except httpx.RequestError:
        raise HTTPException(502, "WiseTech is unavailable.") from None
    except ValueError:
        raise HTTPException(502, "WiseTech returned an invalid response.") from None


def func_wisetech_date(value):
    try:
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value: raise ValueError()
    except ValueError:
        raise HTTPException(400, "effectiveDate must be YYYY-MM-DD.") from None
    return value


def func_wisetech_amount(value, name, positive=False):
    try:
        if isinstance(value, bool): raise ValueError()
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal('1000000000000') or (positive and amount == 0): raise ValueError()
    except (InvalidOperation, ValueError):
        raise HTTPException(400, f"{name} must be a {'positive' if positive else 'non-negative'} finite number.") from None
    return amount


def func_wisetech_list(value):
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise HTTPException(502, "WiseTech returned an invalid list.")
    return value


async def func_wisetech_countries(*, app_state, module_type="ImportHS", effective_date=None):
    if module_type not in ("ImportHS", "ExportHS"): raise HTTPException(400, "Invalid moduleType.")
    params = {"moduleType": module_type}
    if effective_date: params["effectiveDate"] = func_wisetech_date(effective_date)
    return func_wisetech_list(await func_wisetech_request(app_state=app_state, endpoint="get-supported-countries", params=params))


async def func_wisetech_reference(*, app_state, kind, effective_date=None):
    endpoints = {"countries": "get-countries", "destinations": "get-supported-countries", "currencies": "get-currencies", "incoterms": "get-incoterms", "charges": "get-charges"}
    if kind not in endpoints: raise HTTPException(400, "Invalid reference kind.")
    params = {"moduleType": "ImportHS"} if kind == "destinations" else {}
    if effective_date: params["effectiveDate"] = func_wisetech_date(effective_date)
    rows = func_wisetech_list(await func_wisetech_request(app_state=app_state, endpoint=endpoints[kind], params=params))
    if kind in ("countries", "destinations"):
        rows = [row for row in rows if re.fullmatch(r"[A-Z]{2}", str(row.get("code", "")))]
    if kind == "incoterms":
        rows = [row for row in rows if row.get("code") in ("EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP")]
    return rows


def func_wisetech_validate(*, body):
    if not isinstance(body, dict): raise HTTPException(400, "A JSON object is required.")
    if not isinstance(body.get("productDescription", ""), str) or len(body.get("productDescription", "")) > 500:
        raise HTTPException(400, "Product description must be at most 500 characters.")
    destination = body.get("destination", "")
    currency = body.get("currency", "")
    hs = body.get("hsCode", "")
    if not isinstance(destination, str) or not re.fullmatch(r"[A-Z]{2}", destination): raise HTTPException(400, "Select a destination country.")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency): raise HTTPException(400, "Select a currency.")
    if not isinstance(hs, str) or not re.fullmatch(r"[0-9]{6,12}", hs): raise HTTPException(400, "Enter a 6–12 digit destination HS code.")
    if body.get("incoterm") not in ("EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"): raise HTTPException(400, "Select a valid Incoterm.")
    if body.get("transport") not in ("SEA", "AIR", "LAND"): raise HTTPException(400, "Select a transport mode.")
    func_wisetech_date(body.get("effectiveDate"))
    quantity = func_wisetech_amount(body.get("quantity"), "Quantity", True)
    scenarios = body.get("scenarios")
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 4: raise HTTPException(400, "Provide 1–4 origin scenarios.")
    origins = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict): raise HTTPException(400, "Invalid scenario.")
        if not isinstance(scenario.get("assumeGeneralRates", False), bool): raise HTTPException(400, "Invalid general-rate assumption.")
        origin = scenario.get("origin", "")
        if not isinstance(origin, str) or not re.fullmatch(r"[A-Z]{2}", origin): raise HTTPException(400, "Select an origin country.")
        if origin in origins: raise HTTPException(400, "Origins must be unique.")
        origins.add(origin)
        func_wisetech_amount(scenario.get("unitPrice"), "Unit price", True)
        charges = scenario.get("charges", {})
        if not isinstance(charges, dict) or len(charges) > 20: raise HTTPException(400, "Invalid charges.")
        for code, amount in charges.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,30}", code): raise HTTPException(400, "Invalid charge code.")
            func_wisetech_amount(amount, "Charge amount")
    uoms = body.get("unitUomQuantities", [])
    if not isinstance(uoms, list) or len(uoms) > 10: raise HTTPException(400, "Invalid quantities.")
    for item in uoms:
        if not isinstance(item, dict) or not isinstance(item.get("uom"), str) or not re.fullmatch(r"[A-Za-z0-9_ /.-]{1,80}", item["uom"]): raise HTTPException(400, "Invalid quantity unit.")
        func_wisetech_amount(item.get("qty"), "Unit quantity", True)
    if len({x['uom'] for x in uoms}) != len(uoms): raise HTTPException(400, "Quantity units must be unique.")
    return quantity


async def func_wisetech_scenario(*, app_state, body, scenario):
    result = {"origin": scenario["origin"], "status": "needs_review", "currency": body["currency"], "issues": [], "assumptions": ["General duty treatment; preferential eligibility is not assumed.", "Prices and charges are buyer-supplied estimates.", "Pilot calculation: charge basis and total reconciliation require brokerage validation."]}
    common = {"countryOfImportCode": body["destination"], "hsCode": body["hsCode"], "effectiveDate": body["effectiveDate"]}
    lane = {**common, "countryOfOriginCode": scenario["origin"], "countryOfExportCode": scenario["origin"]}
    async def lookup(endpoint, params, method="GET"):
        return func_wisetech_list(await func_wisetech_request(app_state=app_state, endpoint=endpoint, params=params, method=method))
    try:
        # Sequential calls per scenario keep total upstream concurrency at four.
        duties = await lookup("determine-duties", lane)
        accepted = ("Yes", "Maybe") if scenario.get("assumeGeneralRates") else ("Yes",)
        general = next((x for x in duties if x.get("code") == "GR" and x.get("systemDecision") in accepted), None)
        if scenario.get("assumeGeneralRates"):
            result["assumptions"].append("Buyer selected a scenario assuming general duty and candidate standard taxes/fees apply; applicability is unconfirmed.")
        result["dutyOptions"] = [{"code": row.get("code"), "description": row.get("description"), "rate": row.get("dutyRateExpression"), "decision": row.get("systemDecision")} for row in duties]
        if general is None: result["issues"].append("General duty treatment needs brokerage review.")
        selections = {}
        for endpoint, field, transaction in [("determine-taxes", "taxDetails", False), ("determine-fees", "feeDetails", False), ("determine-transaction-taxes", "transactionTaxDetails", True), ("determine-transaction-fees", "transactionFeeDetails", True)]:
            params = {"countryOfImportCode": body["destination"], "effectiveDate": body["effectiveDate"], "modeOfTransport": body["transport"]} if transaction else {**common, "mot": body["transport"], "provinceOfImportCode": "ZZ"}
            rows = await lookup(endpoint, params)
            selections[field] = []
            for row in rows:
                if row.get("systemDecision") == "No": continue
                if row.get("systemDecision") not in accepted or row.get("isConditionalTax") or not row.get("code"):
                    result["issues"].append(f"Review required: {row.get('description') or row.get('code') or endpoint}.")
                else: selections[field].append({"taxFeeCode": row["code"]})
        for endpoint, method in [("determine-add-cvd", "POST"), ("determine-TRQs", "GET")]:
            params = {**lane, "productText": body.get("productDescription", "")} if endpoint == "determine-add-cvd" else lane
            rows = await lookup(endpoint, params, method)
            if any(row.get("systemDecision") != "No" for row in rows): result["issues"].append("Additional duties or quota treatment require brokerage review.")
        supplemental = await lookup("determine-supplemental-hs", {k: v for k, v in lane.items() if k != "hsCode"} | {"primaryHs": body["hsCode"]})
        if any(row.get("systemDecision") != "No" for row in supplemental): result["issues"].append("Supplemental tariff codes require brokerage review.")
        if result["issues"]: return result
        payload = {"countryOfImportCode": body["destination"], "countryOfOriginCode": scenario["origin"], "effectiveDate": body["effectiveDate"], "currencyCode": body["currency"], "unitPrice": float(scenario["unitPrice"]), "quantity": float(body["quantity"]), "incoTerms": body["incoterm"], "modeOfTransport": body["transport"], "hsCode": body["hsCode"], "provinceOfImportCode": "ZZ", "spiCode": "GR", "unitUomQuantities": body.get("unitUomQuantities", []), "charges": {k: float(v) for k,v in scenario.get("charges", {}).items()}, **selections}
        calculated = await func_wisetech_request(app_state=app_state, endpoint="calculate-landed-cost", method="POST", body=payload)
        if not isinstance(calculated, dict) or not re.fullmatch(r"[A-Z]{3}", str(calculated.get("currency", ""))): raise HTTPException(502, "WiseTech returned an invalid calculation currency.")
        calculation_currency = calculated["currency"]
        rate = Decimal(1)
        if calculation_currency != body["currency"]:
            converted = await func_wisetech_request(app_state=app_state, endpoint="convert-currency", params={"sourceCurrency": calculation_currency, "targetCurrency": body["currency"], "value": 1, "effectiveDate": body["effectiveDate"]})
            rate = func_wisetech_amount(converted, "Exchange rate", True)
            result["assumptions"].append(f"Totals converted from {calculation_currency} to {body['currency']} at {rate} for {body['effectiveDate']}.")
        totals = {}
        for target, source in [("landed", "totalAmount"), ("duty", "totalDutyAmount"), ("tax", "totalTaxAmount"), ("fees", "totalFeeAmount"), ("transactionFees", "totalTransactionLevelFeeAmount")]:
            if source not in calculated: raise HTTPException(502, "WiseTech returned an incomplete calculation.")
            totals[target] = str(func_wisetech_amount(calculated[source], "Calculated amount") * rate)
        totals["perUnit"] = str(Decimal(totals["landed"]) / Decimal(str(body["quantity"])))
        totals["goods"] = str(Decimal(str(scenario["unitPrice"])) * Decimal(str(body["quantity"])))
        result.update(status="estimate", totals=totals, breakdownCurrency=calculation_currency, breakdown={k: calculated.get(k, []) for k in ("dutyBreakUp", "taxBreakUp", "feeBreakUp", "transactionLevelFeeBreakUp", "chargeAdjustments")})
        return result
    except HTTPException as exc:
        result.update(status="error", issues=[str(exc.detail)])
        return result


async def func_wisetech_search(*, app_state, body):
    func_wisetech_validate(body=body)
    supported = await func_wisetech_countries(app_state=app_state, effective_date=body["effectiveDate"])
    if body["destination"] not in {x.get("code") for x in supported}: raise HTTPException(400, "Destination HS coverage is unavailable.")
    params = {"tradeType": "Import", "countryCode": body["destination"], "hsCode": body["hsCode"], "effectiveDate": body["effectiveDate"]}
    valid = await func_wisetech_request(app_state=app_state, endpoint="validate-hs", params={**params, "isFinalHSValidation": "true"})
    if not isinstance(valid, dict) or valid.get("isValid") is not True: raise HTTPException(400, "HS code is not a valid final destination code. Confirm it with your broker.")
    required = await func_wisetech_request(app_state=app_state, endpoint="get-hs-uoms", params=params)
    if not isinstance(required, list) or any(not isinstance(x, str) for x in required): raise HTTPException(502, "WiseTech returned invalid units.")
    missing = [x for x in required if x not in {item['uom'] for item in body.get('unitUomQuantities', [])}]
    if missing: return {"status": "needs_input", "requiredUnits": missing, "results": []}
    charges = await func_wisetech_reference(app_state=app_state, kind="charges", effective_date=body["effectiveDate"])
    charge_codes = {x.get("code") for x in charges}
    if any(code not in charge_codes for s in body['scenarios'] for code in s.get('charges', {})): raise HTTPException(400, "An unsupported charge was supplied.")
    results = await asyncio.gather(*(func_wisetech_scenario(app_state=app_state, body=body, scenario=s) for s in body['scenarios']))
    results.sort(key=lambda x: (x['status'] != 'estimate', Decimal(x.get('totals', {}).get('landed', 'Infinity'))))
    return {"status": "finished", "effectiveDate": body["effectiveDate"], "currency": body["currency"], "results": results}
