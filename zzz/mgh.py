AMAZON_STATIC_CONFIG = {
    "supplier": {
        "supplierId": "MGHP",
        "supplierIdType": "SCAC",
        "legalEntityName": "MGH LOGISTICS PRIVATE LIMITED",
        "businessName": "MGH LOGISTICS PRIVATE LIMITED",
        "address": {
            "addressee": "MGH LOGISTICS PRIVATE LIMITED",
            "addressLine1": "Unit No. 1107, 11th Floor, E-Wing, Times Square",
            "addressLine2": "CTS No. 758/759, Marol, Mittal Industrial Estate",
            "addressLine3": "Andheri East",
            "municipalityName": "Mumbai",
            "cityName": "Mumbai",
            "stateName": "MH",
            "countryName": "India",
            "countryCode": "IN",
            "postalCode": "400059"
        }
    },
    "buyer": {
        "address": {
            "addressee": "Attend to : Transportation Finance",
            "addressLine1": "300 Boren Ave N",
            "addressLine2": "NA",
            "addressLine3": "NA",
            "municipalityName": "Seattle",
            "cityName": "Seattle",
            "stateName": "WA",
            "countryName": "United States",
            "countryCode": "US",
            "postalCode": "98109"
        },
        "legalEntityName": "Amazon.com Services LLC",
        "businessName": "Amazon Logistics"
    },
    "billTo": {
        "address": {
            "addressee": "Amazon Logistics, Inc.",
            "addressLine1": "410 Terry Ave N",
            "addressLine2": "Floor 5",
            "addressLine3": "South Lake Union",
            "municipalityName": "Seattle",
            "cityName": "Seattle",
            "stateName": "WA",
            "countryName": "United States",
            "countryCode": "US",
            "postalCode": "98109"
        },
        "legalEntityName": "Amazon.com Services LLC",
        "businessName": "Amazon AP"
    },
    "billFrom": {
        "address": {
            "addressee": "MGH LOGISTICS INC",
            "addressLine1": "67 WALNUT AVE",
            "addressLine2": "SUITE 301",
            "addressLine3": "NA",
            "municipalityName": "CLARK",
            "cityName": "CLARK",
            "stateName": "NJ",
            "countryName": "United States",
            "countryCode": "US",
            "postalCode": "07066"
        },
        "legalEntityName": "MGH LOGISTICS INC",
        "businessName": "MGH LOGISTICS"
    },
    "consigneeAddress": {
        "addressee": "Amazon Fulfillment Center",
        "addressLine1": "2121 8th Ave",
        "addressLine2": "Receiving Dock",
        "addressLine3": "Building 7",
        "municipalityName": "Seattle",
        "cityName": "Seattle",
        "stateName": "WA",
        "countryName": "United States",
        "countryCode": "US",
        "postalCode": "98121"
    }
}



def build_amazon_invoice_payload(row, config):
    try:
        invoice_id = row["INVOICENUMBER"]
    except Exception as e:
        print(f"here is the error: {e}")

    if invoice_id is None or invoice_id.strip() == "":
        raise ValueError("Invoice number is missing in the row data.")

    try:
        payload = {
            "invoiceDocument": {
                #invoiceId should be FBANumber now in the csv previously not there
                # "invoiceId": row["FBANumber"],
                "invoiceId": invoice_id,
                "accountId": row["AccountID"],
                "invoiceDocumentOwner": {
                    "supplierId": config["supplier"]["supplierId"],
                    "supplierIdType": config["supplier"]["supplierIdType"]
                },
                "invoiceHeader": {
                    "invoiceNumber": invoice_id,
                    "purchaseOrderNumber": invoice_id,
                    "invoiceDate": row["INVOICEDATE"],
                    "invoiceAmount": {
                        "amount": float(row["INVOICEAMOUNT"]),
                        "currencyCode": row["CURRENCY"],
                        # "alternateCurrencyAmount": float(row["INVOICEAMOUNT"]),
                        # "alternateCurrencyConversionRate": {
                        #     "sourceCurrencyCode": row["CURRENCY"],
                        #     "targetCurrencyCode": row["CURRENCY"],
                        #     "conversionRate": 1.0,
                        #     "effectiveDate": row["INVOICEDATE"],
                        #     "fxSource": "TRAM_SERVICE"
                        # }
                    },
                    "invoiceAmountWithoutTaxes": {
                        "amount": float(row["INVOICEAMOUNT"]),
                        "currencyCode": row["CURRENCY"],
                        # "alternateCurrencyAmount": float(row["INVOICEAMOUNT"]),
                        # "alternateCurrencyConversionRate": {
                        #     "sourceCurrencyCode": row["CURRENCY"],
                        #     "targetCurrencyCode": row["CURRENCY"],
                        #     "conversionRate": 1.0,
                        #     #check the payload without effectivdate once
                        #     "effectiveDate": row["INVOICEDATE"],
                        #     "fxSource": "TRAM_SERVICE"
                        # }
                    },
                    "invoiceReferences": [
                        {
                            # "invoiceId": row["FBANumber"],
                            "invoiceId": invoice_id,
                            "invoiceNumber": invoice_id
                        }
                    ],
                    "buyer": {
                        "legalEntity": {
                            "addresses": [config["buyer"]["address"]],
                            "taxIdentities": [
                                {
                                    "taxIdentityNumber": "32-0765633",
                                    "taxIdentityType": "VAT"
                                }
                            ],
                            "legalEntityName": config["buyer"]["legalEntityName"],
                            "businessName": config["buyer"]["businessName"]
                        }
                    },
                    "supplier": {
                        "legalEntity": {
                            "addresses": [config["supplier"]["address"]],
                            "taxIdentities": [
                                {
                                    "taxIdentityNumber": "27AAECM2361B1ZW",
                                    "taxIdentityType": "VAT"
                                }
                            ],
                            "legalEntityName": config["supplier"]["legalEntityName"],
                            "businessName": config["supplier"]["businessName"]
                        }
                    },
                    "billTo": {
                        "legalEntity": {
                            "addresses": [config["billTo"]["address"]],
                            "taxIdentities": [
                                {
                                    "taxIdentityNumber": "32-0765633",
                                    "taxIdentityType": "VAT"
                                }
                            ],
                            "legalEntityName": config["billTo"]["legalEntityName"],
                            "businessName": config["billTo"]["businessName"]
                        }
                    },
                    "billFrom": {
                        "legalEntity": {
                            "addresses": [config["billFrom"]["address"]],
                            "taxIdentities": [
                                {
                                    "taxIdentityNumber": "32-0765633",
                                    "taxIdentityType": "VAT"
                                }
                            ],
                            "legalEntityName": config["billFrom"]["legalEntityName"],
                            "businessName": config["billFrom"]["businessName"]
                        }
                    },
                    "documentTypeInfo": {
                        "documentType": "INVOICE",
                        "requestForPayment": True
                    }
                },
                "invoiceLineItems": [
                    {
                        "lineItemId": "1",
                        "description": row["DESCRIPTION"],
                        "lineItemRequisitionIdentifierInfo": {
                            "primaryRefId": {
                                "extensions": [
                                    {"trackingId": row["TRACKINGID"]}
                                    # {"trackingId":"BM49014389B"}
                                ]
                            }
                        },
                        "lineItemDetail": {
                            "freightShipmentDetail": {
                                # substitute with SHIPMENTIDENTIFICATION
                                # "shipmentIdentificationNumber": row["SHIPMENTIDENTIFICATION"],
                                "shipmentIdentificationNumber": row["FBANumber"],
                                # "shipmentIdentificationNumber": "FBA194M16R3T",
                                # substitute with SHIPMENTBILLOFLADINGNUMBER
                                "shipmentBillOfLadingNumber": row["SHIPMENTBILLOFLADINGNUMBER"],
                                "proofOfDelivery": row["PROOFOFDELIVERY"],
                                "consigneeAddress": config["consigneeAddress"],
                                "transportationMethodType": row["TRANSPORTATIONMETHODTYPE"],
                                "shippedDate": row["SHIPPEDDATE"],
                                "deliveryDate": row["DELIVERYDATE"],
                                "shipmentWeightDetail": {
                                    "grossWeight": {
                                        "weight": float(row["GROSSWEIGHT"]),
                                        "unitOfMeasurement": "KG"
                                    },
                                    "netWeight": {
                                        "weight": float(row["GROSSWEIGHT"]),
                                        "unitOfMeasurement": "KG"
                                    },
                                    "billedWeight": {
                                        "weight": float(row["GROSSWEIGHT"]),
                                        "unitOfMeasurement": "KG"
                                    },
                                    "declaredWeight": {
                                        "weight": float(row["GROSSWEIGHT"]),
                                        "unitOfMeasurement": "KG"
                                    }
                                },
                                "shipmentVolumeDetail": {
                                    "billedVolume": {
                                        "length": float(row["VOLUMELENGTH"]),
                                        "breadth": float(row["VOLUMEBREADTH"]),
                                        "height": float(row["VOLUMEHEIGHT"]),
                                        "unitOfMeasurement": row["UOM"]
                                    },
                                    "declaredVolume": {
                                        "length": float(row["VOLUMELENGTH"]),
                                        "breadth": float(row["VOLUMEBREADTH"]),
                                        "height": float(row["VOLUMEHEIGHT"]),
                                        "unitOfMeasurement": row["UOM"]
                                    }
                                },
                                "packageDetails": [
                                    {
                                        "packageReferenceId": row["CHARGEID"],
                                        "packageWeightDetail": {
                                            "grossWeight": {
                                                "weight": float(row["GROSSWEIGHT"]),
                                                "unitOfMeasurement": "KG"
                                            },
                                            "netWeight": {
                                                "weight": float(row["GROSSWEIGHT"]),
                                                "unitOfMeasurement": "KG"
                                            },
                                            "billedWeight": {
                                                "weight": float(row["GROSSWEIGHT"]),
                                                "unitOfMeasurement": "KG"
                                            },
                                            "declaredWeight": {
                                                "weight": float(row["GROSSWEIGHT"]),
                                                "unitOfMeasurement": "KG"
                                            }
                                        },
                                        "packageVolumeDetail": {
                                            "billedVolume": {
                                                "length": float(row["VOLUMELENGTH"]),
                                                "breadth": float(row["VOLUMEBREADTH"]),
                                                "height": float(row["VOLUMEHEIGHT"]),
                                                "unitOfMeasurement": row["UOM"]
                                            },
                                            "declaredVolume": {
                                                "length": float(row["VOLUMELENGTH"]),
                                                "breadth": float(row["VOLUMEBREADTH"]),
                                                "height": float(row["VOLUMEHEIGHT"]),
                                                # try with CBM once
                                                "unitOfMeasurement": row["UOM"]
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                        "unitCharges": [],
                        "quantity": {
                            "quantity": 1.0,
                            "quantityUnit": "COUNT"
                        },
                        "lineItemAmount": {
                            "amount": float(row["INVOICEAMOUNT"]),
                            "currencyCode": row["CURRENCYCODE"]
                        },
                        "lineItemAmountWithoutTaxes": {
                            "amount": float(row["INVOICEAMOUNT"]),
                            "currencyCode": row["CURRENCYCODE"]
                        }
                    }
                ]
            }
        }

        return payload

    except Exception as e:
        print(f"here is the error end: {e}")



def append_unit_charge(payload, row):
    try:
        charge_amount = float(row["AMOUNT"])
    except Exception as e:
        print(f"here is the error in unit charges: {e}")

    try:
        unit_charge = {
            "chargeId": row["CHARGEID"],
            "chargeCode": row["CHARGECODE"],
            "chargeAmount": {
                "amount": charge_amount,
                "currencyCode": row["CURRENCYCODE"],
                #alternateCurrencyAmount there can be changes in future if needed check the api without it also once
                # "alternateCurrencyAmount": charge_amount,
                # "alternateCurrencyConversionRate": {
                #     "sourceCurrencyCode": row["CURRENCYCODE"],
                #     "targetCurrencyCode": row["CURRENCYCODE"],
                #     "conversionRate": 1.0,
                #     "effectiveDate": row["INVOICEDATE"],
                #     "fxSource": "TRAM_SERVICE"
                # }
            }
        }

        line_item = payload["invoiceDocument"]["invoiceLineItems"][0]

        # Append charge
        line_item["unitCharges"].append(unit_charge)

        # Update totals
        # line_item["lineItemAmount"]["amount"] += charge_amount
        # line_item["lineItemAmountWithoutTaxes"]["amount"] += charge_amount

        header = payload["invoiceDocument"]["invoiceHeader"]
        # header["invoiceAmount"]["amount"] += charge_amount
        # header["invoiceAmountWithoutTaxes"]["amount"] += charge_amount

    except Exception as e:
        print(f"here is the error lol: {e}")


from datetime import datetime, timedelta, timezone
def format_amazon_datetime(date_str: str | None) -> str:
    # Fallback: today at 00:00:00 UTC
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")

    if not date_str or date_str == "00000000":
        return today_utc

    try:
        dt = datetime.strptime(date_str.strip(), "%Y%m%d")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return today_utc


from datetime import datetime, timezone, timedelta
import httpx, os
_token=None; _expires_at=None
async def func_get_amazon_token():
    AMAZON_TOKEN_URL="https://sendstack-prod-token.auth.us-east-1.amazoncognito.com/oauth2/token"
    global _token,_expires_at
    now=datetime.now(timezone.utc)
    if _token and _expires_at and now<_expires_at: return _token
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(AMAZON_TOKEN_URL,data={"grant_type":"client_credentials","client_id":os.getenv("config_client_id_amazon"),"client_secret":os.getenv("config_client_secret_amazon")},headers={"Content-Type":"application/x-www-form-urlencoded"})
    r.raise_for_status()
    _token=r.json()["access_token"]; _expires_at=now+timedelta(minutes=55)
    return _token


import httpx
async def func_send_invoice_to_amazon(payload, amazon_access_token):
    # print(payload)
    # AMAZON_SEND_INVOICE_URL = "https://gamma.send.irisapi.iris.ctt.amazon.dev/sendInvoiceDocument"
    AMAZON_SEND_INVOICE_URL = "https://prod.send.irisapi.iris.ctt.amazon.dev/sendInvoiceDocument"
    AMAZON_CLIENT_CERT_PATH = "secret/mgh-cert.txt"
    AMAZON_CLIENT_KEY_PATH = "secret/mgh-pv.key"
    headers = {
        "Authorization": f"Bearer {amazon_access_token}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(
        timeout=60,
        cert=(AMAZON_CLIENT_CERT_PATH, AMAZON_CLIENT_KEY_PATH)
    ) as client:
        response = await client.post(
            AMAZON_SEND_INVOICE_URL,
            json=payload,
            headers=headers
        )
    if response.status_code in (200, 202):
        return {
            "success": True,
            "status_code": response.status_code,
            "body": response.json() if response.content else None,
            "request_id": response.headers.get("x-amzn-RequestId")
        }
    return {
        "success": False,
        "status_code": response.status_code,
        "error_body": response.text,
        "request_id": response.headers.get("x-amzn-RequestId")
    }


async def log_invoice_error(request, invoice_id, filename, stage, error, payload=None):
    try:
        db_object = {
            "invoice_id": invoice_id,
            "created_at": datetime.now(timezone.utc),
            "payload": json.dumps(payload) if payload else None,
            "filename": filename,
            "response": json.dumps({"error": str(error), "stage": stage}),
            "status": 0
        }

        await request.app.state.func_postgres_obj_create(
            mode="now",
            client_postgres_pool=request.app.state.client_postgres_pool,
            table="invoice",
            obj_list=[db_object],
            returning_ids=False,
            func_postgres_obj_serialize=request.app.state.func_postgres_obj_serialize,
            cache_postgres_column_datatype=request.app.state.cache_postgres_column_datatype
        )
    except Exception as db_err:
        print("ERROR: failed while logging invoice error:", db_err)



async def func_send_invoice(request, func_get_amazon_token, build_amazon_invoice_payload, append_unit_charge,func_send_invoice_to_amazon):
    try:
        if request.app.state.client_sftp:
            try:
                output = await request.app.state.func_sftp_folder_filename_read(request.app.state.client_sftp,"mgh/amazon")
                print("files to download:", output)
            except Exception as e:
                print("ERROR: Failed while reading SFTP folder:", e)
                raise
            for filename in output:
                if filename == "." or filename == ".." or not filename.lower().endswith(".csv"):
                    continue
                try:
                    try:
                        await request.app.state.func_sftp_file_download(
                            request.app.state.client_sftp,
                            f"mgh/amazon/{filename}",
                            f"export/mgh/{filename}"
                        )
                    except Exception as e:
                        print(f"ERROR: File download failed for {filename}:", e)
                        continue
                    try:
                        amazon_access_token = await func_get_amazon_token()
                    except Exception as e:
                        print("ERROR: Failed to fetch Amazon token:", e)
                        continue

                    try:
                        csv_obj = request.app.state.func_csv_to_obj_list(f"export/mgh/{filename}")
                        print(f"Rows parsed: {len(csv_obj)}")
                    except Exception as e:
                        print(f"ERROR: Failed parsing CSV for {filename}:", e)
                        continue

                    all_payloads = []
                    amazon_responses = []

                    # agar approach mein ye hua har chargecode ke liye alag line item banana hua toh 
                    # for row in csv_obj:
                    #     amazon_payload = build_amazon_invoice_payload(row, AMAZON_STATIC_CONFIG)
                    #     # all_payloads.append(amazon_payload)

                    try:
                        invoices = {}
                        for row in csv_obj:
                            invoice_id = row["INVOICENUMBER"]

                            try:
                                row["INVOICEDATE"] = format_amazon_datetime(row["INVOICEDATE"])
                                row["UOM"]= "GALLONS"
                                # row["UOM"]= "KG"
                                row["SHIPPEDDATE"] = format_amazon_datetime(row["SHIPPEDDATE"])
                                row["DELIVERYDATE"] = format_amazon_datetime(row["DELIVERYDATE"])
                            except Exception as e:
                                print(f"ERROR: Date/UOM formatting failed for row {row}:", e)
                                continue

                            try:
                                if invoice_id not in invoices:
                                    invoices[invoice_id] = build_amazon_invoice_payload(row, AMAZON_STATIC_CONFIG)
                            except Exception as e:
                                print(f"ERROR: Failed building base invoice payload for {invoice_id} {filename}:", e)
                                await log_invoice_error(request, invoice_id, filename, "payload_build", e, payload=None)
                                continue

                            try:
                                append_unit_charge(invoices[invoice_id], row)
                            except Exception as e:
                                print(f"ERROR: append_unit_charge failed for invoice {invoice_id}:", e)
                                await log_invoice_error(request, invoice_id, filename, "append_unit_charge", e, invoices.get(invoice_id))
                                continue
                    except Exception as e:
                        print(f"ERROR: Failure while constructing invoice payloads for {filename}:", e)
                        continue
                    
                    
                    try:
                        for final_payload in invoices.values():
                            # only used to produce  json file for reference
                            all_payloads.append(final_payload)

                            # try:
                            #     final_payload = json.loads(row["payload"])
                            # except Exception as e:
                            #     print("ERROR: Failed loading payload JSON:", e)
                            #     continue

                            # with open("C:/Users/omsri/Desktop/mgh freelance/atom/zzz/sample.json", "r") as f:
                            #     gfg = json.load(f)
                            # print(gfg)

                            try:
                                amazon_response = await func_send_invoice_to_amazon(final_payload,amazon_access_token)
                                print(amazon_response)
                                amazon_responses.append(amazon_response)
                            except Exception as e:
                                print("ERROR: Failed sending invoice to Amazon:", e)
                                await log_invoice_error(request, invoice_id, filename, "amazon_send", e, final_payload)
                                continue

                            try:
                                db_object = {
                                    "invoice_id": invoice_id,
                                    "created_at": datetime.now(timezone.utc),
                                    "payload": json.dumps(final_payload),
                                    "filename": filename,
                                    "response": json.dumps(
                                        amazon_response.get("body")
                                        if amazon_response["success"]
                                        else amazon_response.get("error_body")
                                    ),
                                    "status": 1 if amazon_response["success"] else 0
                                }

                                await request.app.state.func_postgres_obj_create(
                                    mode="now",
                                    client_postgres_pool=request.app.state.client_postgres_pool,
                                    table="invoice",
                                    obj_list=[db_object],
                                    returning_ids=False,
                                    func_postgres_obj_serialize=request.app.state.func_postgres_obj_serialize,
                                    cache_postgres_column_datatype=request.app.state.cache_postgres_column_datatype
                                )
                            except Exception as e:
                                print("ERROR: Failed inserting DB record:", e)
                                continue

                            # to delete the file from sftp server after successful send
                            # if amazon_response["success"]:
                                # await func_sftp_file_delete(request.app.state.client_sftp,f"mgh/amazon/{filename}")

                        json_name = filename.replace(".csv", ".json")
                        local_json_path = f"export/mgh/{json_name}"
                        with open(local_json_path, "w") as f:
                            json.dump(all_payloads, f)

                        json_name = filename.replace(".csv", ".json")
                        local_json_path = f"static/mgh/{json_name}"
                        os.makedirs("static/mgh", exist_ok=True)
                        with open(local_json_path, "w") as f:
                            json.dump(amazon_responses, f)

                        # Upload generated JSON to SFTP server (same path as original CSV)
                        # try:
                        #     await request.app.state.func_sftp_file_upload(
                        #         request.app.state.client_sftp,
                        #         local_json_path,
                        #         f"mgh/amazon/{json_name}"
                        #     )
                        #     print(f"Successfully uploaded {json_name} to SFTP")
                        # except Exception as e:
                        #     print(f"ERROR: Failed to upload {json_name} to SFTP:", e)

                    except Exception as e:
                        print(f"ERROR: Failure while processing final payload stage {filename}:", e)
                        continue

                except Exception as e:
                    print(f"{filename}: Unexpected error occurred:", e)

            return {"status":1,"message":"done"}

        else:
            raise Exception(f"sftp client not connected")

    except Exception as e:
        print("FATAL ERROR in custom_function_send_invoice_mgh:", e)
        raise
