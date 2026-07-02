# packages
from fastapi import APIRouter, Request, Response
from fastapi.encoders import jsonable_encoder
import os

# router
router = APIRouter()

# helper
def helper_sql_visible_shipments_owned(name="visible_shipments"):
    return f"""{name} AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.cvw_JobShipmentOrgs AS JSO ON JSO.JS_PK = JS.JS_PK
            WHERE JS.JS_IsValid = 1
              AND JSO.ControllingCustomer_PK = @org
        )"""

def helper_sql_visible_shipments(name="visible_shipments", with_shipment_id=False, with_declaration=False, with_search=False):
    je_join = "LEFT JOIN dbo.JobDeclaration AS JE ON JE.JE_JS = JS.JS_PK AND JE.JE_IsValid = 1" if with_declaration else ""
    shipment_id_filter = "AND (@shipment_id IS NULL OR JS.JS_PK = @shipment_id)" if with_shipment_id else ""
    je_org = ("""
                        OR JE.JE_OH_Importer = @org
                        OR JE.JE_OH_Supplier = @org
                        OR JE.JE_OH_Buyer = @org
                        OR JE.JE_OH_Consignee = @org
                        OR JE.JE_OH_Exporter = @org
                        OR JE.JE_OH_Forwarder = @org
                        OR JE.JE_OH_ControllingCustomer = @org
                        OR JE.JE_OH_ControllingAgent = @org""" if with_declaration else "")
    search_filter = ("""
            AND (
                @shipment_search = ''
                OR CONVERT(varchar(36), JS.JS_PK) = @shipment_search
                OR JS.JS_UniqueConsignRef LIKE '%' + @shipment_search + '%'
                OR JS.JS_BookingReference LIKE '%' + @shipment_search + '%'
                OR JS.JS_HouseBill LIKE '%' + @shipment_search + '%'
                OR JS.JS_ConsolReference LIKE '%' + @shipment_search + '%'
                OR EXISTS (
                    SELECT 1
                    FROM dbo.JobHeader AS JHSearch
                    WHERE JHSearch.JH_ParentID = JS.JS_PK
                      AND JHSearch.JH_ParentTableCode = 'JS'
                      AND JHSearch.JH_JobNum LIKE '%' + @shipment_search + '%'
                )
            )""" if with_search else "")
    return f"""{name} AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.cvw_JobShipmentOrgs AS JSO ON JSO.JS_PK = JS.JS_PK
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            {je_join}
            WHERE JS.JS_IsValid = 1
            {shipment_id_filter}
            AND (
                (@view_as = 'controlling_customer' AND JSO.ControllingCustomer_PK = @org)
                OR (
                    @view_as = 'all'
                    AND (
                        JSO.ControllingCustomer_PK = @org
                        OR JS.JS_OH_Creditor = @org
                        OR JS.JS_OH_DeliveryAgent = @org
                        OR JS.JS_OH_ExportBroker = @org
                        OR JS.JS_OH_HandledOnBehalfOfForwarder = @org
                        OR JS.JS_OH_ImportBroker = @org
                        OR JS.JS_OH_TranshipAgent = @org
                        OR E2OA.OA_OH = @org
                        OR BuyerOA.OA_OH = @org
                        OR SupplierOA.OA_OH = @org
                        OR JD.JD_OH_Carrier = @org
                        OR JD.JD_OH_SendingAgent = @org
                        OR JD.JD_OH_ReceivingAgent = @org{je_org}
                    )
                )
            ){search_filter}
        )"""

# api
@router.get("/myshipment/my-account")
async def func_api_myshipment_my_account(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    role_map = {
        "is_consignee": "Consignee",
        "is_consignor": "Consignor",
        "is_transport_client": "Transport Client",
        "is_warehouse_client": "Warehouse Client",
        "is_forwarder": "Forwarder",
        "is_shipping_provider": "Shipping Provider",
        "is_air_wholesaler": "Air Wholesaler",
        "is_sea_wholesaler": "Sea Wholesaler",
        "is_rail_provider": "Rail Provider",
        "is_line_haul_provider": "Line Haul Provider",
        "is_misc_freight_services": "Miscellaneous Freight Services",
        "is_air_cto": "Air CTO",
        "is_air_line": "Airline",
        "is_broker": "Broker",
        "is_container_yard": "Container Yard",
        "is_local_transport": "Local Transport",
        "is_pack_depot": "Pack Depot",
        "is_sea_cto": "Sea CTO",
        "is_shipping_line": "Shipping Line",
        "is_unpack_depot": "Unpack Depot",
        "is_rail_head": "Rail Head",
        "is_road_freight_depot": "Road Freight Depot",
        "is_shipping_consortium": "Shipping Consortium",
        "is_fumigation_contractor": "Fumigation Contractor",
        "is_distribution_centre": "Distribution Centre",
        "is_controlling_customer": "Controlling Customer",
        "is_controlling_agent": "Controlling Agent",
        "is_ferry_water_terminal": "Ferry / Water Terminal",
        "is_container_leasing_company": "Container Leasing Company",
        "is_inland_waterway_provider": "Inland Waterway Provider",
        "is_vgm_contractor": "VGM Contractor",
    }
    classification_map = {
        "is_global_account": "Global Account",
        "is_national_account": "National Account",
        "is_sales_lead": "Sales Lead",
        "is_competitor": "Competitor",
        "is_temp_account": "Temporary Account",
        "is_personal_effects_account": "Personal Effects Account",
    }
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            SELECT
                CONVERT(varchar(36), OH.OH_PK) AS org_id,
                OH.OH_Code AS org_code,
                OH.OH_FullName AS name,
                OH.OH_IsActive AS is_active,
                OH.OH_IsValid AS is_valid,
                OH.OH_Category AS category,
                OH.OH_Language AS language,
                OH.OH_RL_NKClosestPort AS closest_port,
                OH.OH_ScreeningStatus AS screening_status,
                CASE WHEN OH.OH_SystemCreateTimeUtc IS NULL THEN NULL ELSE CONVERT(varchar(33), OH.OH_SystemCreateTimeUtc, 126) + 'Z' END AS created_at,
                CASE WHEN OH.OH_SystemLastEditTimeUtc IS NULL THEN NULL ELSE CONVERT(varchar(33), OH.OH_SystemLastEditTimeUtc, 126) + 'Z' END AS updated_at,
                OH.OH_IsConsignee AS is_consignee,
                OH.OH_IsConsignor AS is_consignor,
                OH.OH_IsTransportClient AS is_transport_client,
                OH.OH_IsWarehouseClient AS is_warehouse_client,
                OH.OH_IsForwarder AS is_forwarder,
                OH.OH_IsShippingProvider AS is_shipping_provider,
                OH.OH_IsAirWholesaler AS is_air_wholesaler,
                OH.OH_IsSeaWholesaler AS is_sea_wholesaler,
                OH.OH_IsRailProvider AS is_rail_provider,
                OH.OH_IsLineHaulProvider AS is_line_haul_provider,
                OH.OH_IsMiscFreightServices AS is_misc_freight_services,
                OH.OH_IsAirCTO AS is_air_cto,
                OH.OH_IsAirLine AS is_air_line,
                OH.OH_IsBroker AS is_broker,
                OH.OH_IsContainerYard AS is_container_yard,
                OH.OH_IsLocalTransport AS is_local_transport,
                OH.OH_IsPackDepot AS is_pack_depot,
                OH.OH_IsSeaCTO AS is_sea_cto,
                OH.OH_IsShippingLine AS is_shipping_line,
                OH.OH_IsUnpackDepot AS is_unpack_depot,
                OH.OH_IsRailHead AS is_rail_head,
                OH.OH_IsRoadFreightDepot AS is_road_freight_depot,
                OH.OH_IsShippingConsortium AS is_shipping_consortium,
                OH.OH_IsFumigationContractor AS is_fumigation_contractor,
                OH.OH_IsGlobalAccount AS is_global_account,
                OH.OH_IsNationalAccount AS is_national_account,
                OH.OH_IsSalesLead AS is_sales_lead,
                OH.OH_IsCompetitor AS is_competitor,
                OH.OH_IsTempAccount AS is_temp_account,
                OH.OH_IsPersonalEffectsAccount AS is_personal_effects_account,
                OH.OH_IsDistributionCentre AS is_distribution_centre,
                OH.OH_IsControllingCustomer AS is_controlling_customer,
                OH.OH_IsControllingAgent AS is_controlling_agent,
                OH.OH_IsFerryWaterTerminal AS is_ferry_water_terminal,
                OH.OH_IsContainerLeasingCompany AS is_container_leasing_company,
                OH.OH_IsInlandWaterwayProvider AS is_inland_waterway_provider,
                OH.OH_IsVGMContractor AS is_vgm_contractor
            FROM dbo.OrgHeader AS OH
            WHERE OH.OH_PK = TRY_CONVERT(uniqueidentifier, ?);""", org_pk)
        org_columns = [column[0] for column in cursor.description]
        org_rows = [dict(zip(org_columns, row)) for row in await cursor.fetchall()]
        if not org_rows: raise Exception("Organization profile not found")
        org = org_rows[0]
        roles = [label for key, label in role_map.items() if org.pop(key, None)]
        classifications = [label for key, label in classification_map.items() if org.pop(key, None)]
        await cursor.execute("""
            SELECT TOP 50
                CONVERT(varchar(36), OA.OA_PK) AS address_id,
                OA.OA_Code AS code,
                OA.OA_CompanyNameOverride AS company_name,
                OA.OA_Address1 AS address_1,
                OA.OA_Address2 AS address_2,
                OA.OA_City AS city,
                OA.OA_State AS state,
                OA.OA_PostCode AS post_code,
                OA.OA_RN_NKCountryCode AS country_code,
                OA.OA_ValidationStatus AS validation_status,
                OA.OA_RL_NKRelatedPortCode AS related_port,
                OA.OA_Phone AS phone,
                OA.OA_Mobile AS mobile,
                OA.OA_Email AS email,
                CASE WHEN OA.OA_SystemLastEditTimeUtc IS NULL THEN NULL ELSE CONVERT(varchar(33), OA.OA_SystemLastEditTimeUtc, 126) + 'Z' END AS updated_at
            FROM dbo.OrgAddress AS OA
            WHERE OA.OA_OH = TRY_CONVERT(uniqueidentifier, ?)
              AND OA.OA_IsValid = 1
              AND OA.OA_IsActive = 1
            ORDER BY OA.OA_Code, OA.OA_PK;""", org_pk)
        address_columns = [column[0] for column in cursor.description]
        addresses = [dict(zip(address_columns, row)) for row in await cursor.fetchall()]
        await cursor.execute("""
            SELECT TOP 50
                CONVERT(varchar(36), OC.OC_PK) AS contact_id,
                OC.OC_ContactName AS name,
                OC.OC_Title AS title,
                OC.OC_Phone AS phone,
                OC.OC_PhoneExtension AS phone_extension,
                OC.OC_Mobile AS mobile,
                OC.OC_Email AS email,
                OC.OC_WebAccessEnabled AS web_access_enabled,
                OA.OA_Code AS address_code,
                CASE WHEN OC.OC_SystemLastEditTimeUtc IS NULL THEN NULL ELSE CONVERT(varchar(33), OC.OC_SystemLastEditTimeUtc, 126) + 'Z' END AS updated_at
            FROM dbo.OrgContact AS OC
            LEFT JOIN dbo.OrgAddress AS OA
              ON OA.OA_PK = OC.OC_OA_OrgAddress
             AND OA.OA_IsValid = 1
            WHERE OC.OC_OH = TRY_CONVERT(uniqueidentifier, ?)
              AND OC.OC_IsValid = 1
              AND OC.OC_IsActive = 1
            ORDER BY OC.OC_ContactName, OC.OC_PK;""", org_pk)
        contact_columns = [column[0] for column in cursor.description]
        contacts = [dict(zip(contact_columns, row)) for row in await cursor.fetchall()]
    profile_object = {"org": org, "roles": roles, "classifications": classifications, "addresses": addresses, "contacts": contacts}
    return {"status": 1, "message": jsonable_encoder(profile_object)}

@router.get("/myshipment/my-purchase-orders")
async def func_api_myshipment_my_purchase_orders(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("po_number", "str", 0, None, ""), ("shipment_id", "str", 0, None, ""), ("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer")])
    limit = int(oq["limit"] or app_state.config_sql_read_limit_default)
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    limit = max(1, limit)
    page = max(1, int(oq["page"] or 1))
    offset = (page - 1) * limit
    sql_limit = limit + 1
    po_number = str(oq.get("po_number") or "").strip()
    shipment_id = str(oq.get("shipment_id") or "").strip()
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @po_number nvarchar(max) = ?;
        DECLARE @shipment_id_str nvarchar(max) = ?;
        DECLARE @view_as nvarchar(40) = ?;
        DECLARE @shipment_id_requested bit = CASE WHEN @shipment_id_str <> '' THEN 1 ELSE 0 END;
        DECLARE @shipment_id uniqueidentifier = TRY_CONVERT(uniqueidentifier, @shipment_id_str);
        WITH """ + helper_sql_visible_shipments_owned(name='visible_shipments') + f""",
        visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.cvw_JobShipmentOrgs AS JSO ON JSO.JS_PK = JD.JD_JS
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              { "AND JD.JD_OrderNumber = @po_number" if po_number else "" }
              AND (
                    @shipment_id_requested = 0
                 OR JD.JD_JS = @shipment_id
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOShipment
                        JOIN dbo.JobSupplierBookingLine AS JSLShipment ON JSLShipment.JSL_JO_OrderLine = JOShipment.JO_PK AND JSLShipment.JSL_IsValid = 1
                        JOIN dbo.JobPackLines AS JLShipment ON JLShipment.JL_JSL_BookingLine = JSLShipment.JSL_PK AND JLShipment.JL_IsValid = 1
                        WHERE JOShipment.JO_JD = JD.JD_PK
                          AND JOShipment.JO_IsValid = 1
                          AND JLShipment.JL_JS = @shipment_id
                    )
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOShipment
                        JOIN dbo.JobSupplierBookingLine AS JSLShipment ON JSLShipment.JSL_JO_OrderLine = JOShipment.JO_PK AND JSLShipment.JSL_IsValid = 1
                        JOIN dbo.JobContainer AS JCShipment ON JCShipment.JC_JSB_SupplierBooking = JSLShipment.JSL_JSB_Booking AND JCShipment.JC_IsValid = 1
                        WHERE JOShipment.JO_JD = JD.JD_PK
                          AND JOShipment.JO_IsValid = 1
                          AND JCShipment.JC_JS_FCLBookingOnlyLink = @shipment_id
                    )
              )
              AND (
                    -- Controlling-customer view: the buyer on the PO is the logged-in org
                    BuyerOA.OA_OH = @org
                 OR JD.JD_JS IN (SELECT JS_PK FROM visible_shipments)
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobPackLines AS JLVisible ON JLVisible.JL_JSL_BookingLine = JSLVisible.JSL_PK AND JLVisible.JL_IsValid = 1
                        JOIN visible_shipments AS VSVisible ON VSVisible.JS_PK = JLVisible.JL_JS
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobContainer AS JCVisible ON JCVisible.JC_JSB_SupplierBooking = JSLVisible.JSL_JSB_Booking AND JCVisible.JC_IsValid = 1
                        JOIN visible_shipments AS VSVisible ON VSVisible.JS_PK = JCVisible.JC_JS_FCLBookingOnlyLink
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR (
                        @view_as = 'all'
                    AND (
                           JSO.ControllingCustomer_PK = @org
                        OR BuyerOA.OA_OH = @org
                        OR SupplierOA.OA_OH = @org
                        OR JD.JD_OH_Carrier = @org
                        OR JD.JD_OH_SendingAgent = @org
                        OR JD.JD_OH_ReceivingAgent = @org
                        OR EXISTS (
                            SELECT 1
                            FROM dbo.JobOrderLine AS JO
                            WHERE JO.JO_JD = JD.JD_PK
                              AND JO.JO_IsValid = 1
                              AND JO.JO_OH_Supplier = @org
                        )
                    )
                 )
              )
        ),
        line_summary AS (
            SELECT
                JO.JO_JD AS order_pk,
                COUNT(1) AS line_count,
                SUM(JO.JO_Quantity) AS total_quantity,
                SUM(JO.JO_LinePrice) AS total_value,
                SUM(JO.JO_ActualWeight) AS total_weight,
                SUM(JO.JO_ActualVolume) AS total_volume
            FROM dbo.JobOrderLine AS JO
            WHERE JO.JO_IsValid = 1
            GROUP BY JO.JO_JD
        )
        SELECT
            CONVERT(varchar(36), JD.JD_PK) AS purchase_order_id,
            JD.JD_OrderNumber AS order_number,
            JD.JD_OrderNumberSplit AS order_split,
            JD.JD_CustomerReference AS customer_reference,
            JD.JD_OrderStatus AS status,
            JD.JD_IsCancelled AS is_cancelled,
            JD.JD_IsReleased AS is_released,
            JD.JD_IsPriority AS is_priority,
            JD.JD_OrderDate AS order_date,
            JD.JD_ShipmentWindowStart AS shipment_window_start,
            JD.JD_ShipmentWindowEnd AS shipment_window_end,
            JD.JD_ExWorksRequiredBy AS ex_works_required_by,
            JD.JD_DeliveryRequiredBy AS delivery_required_by,
            JD.JD_TransportMode AS transport_mode,
            JD.JD_ContainerMode AS container_mode,
            JD.JD_IncoTerm AS inco_term,
            JD.JD_OrderGoodsDescription AS goods_description,
            JD.JD_RL_NKPortOfLoading AS port_of_loading,
            JD.JD_RL_NKPortOfDischarge AS port_of_discharge,
            BuyerOH.OH_Code AS buyer_code,
            BuyerOH.OH_FullName AS buyer_name,
            SupplierOH.OH_Code AS supplier_code,
            SupplierOH.OH_FullName AS supplier_name,
            COALESCE(CONVERT(varchar(36), JD.JD_JS), CONVERT(varchar(36), LinkedShipment.JS_PK)) AS shipment_id,
            CASE WHEN COALESCE(JD.JD_JS, LinkedShipment.JS_PK) IS NULL THEN 0 ELSE 1 END AS has_shipment,
            COALESCE(LS.line_count, 0) AS line_count,
            LS.total_quantity,
            LS.total_value,
            LS.total_weight,
            LS.total_volume,
            JD.JD_SystemCreateTimeUtc AS created_at,
            JD.JD_SystemLastEditTimeUtc AS updated_at
        FROM visible_orders AS VO
        JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK
        LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
        LEFT JOIN dbo.OrgHeader AS BuyerOH ON BuyerOH.OH_PK = BuyerOA.OA_OH
        LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
        LEFT JOIN dbo.OrgHeader AS SupplierOH ON SupplierOH.OH_PK = SupplierOA.OA_OH
        LEFT JOIN line_summary AS LS ON LS.order_pk = JD.JD_PK
        OUTER APPLY (
            SELECT TOP 1 LinkRows.JS_PK
            FROM (
                SELECT JL.JL_JS AS JS_PK, JL.JL_PK AS sort_key
                FROM dbo.JobOrderLine AS JO
                JOIN dbo.JobSupplierBookingLine AS JSL ON JSL.JSL_JO_OrderLine = JO.JO_PK AND JSL.JSL_IsValid = 1
                JOIN dbo.JobPackLines AS JL ON JL.JL_JSL_BookingLine = JSL.JSL_PK AND JL.JL_IsValid = 1
                WHERE JO.JO_JD = JD.JD_PK
                  AND JO.JO_IsValid = 1
                  AND JL.JL_JS IS NOT NULL
                UNION ALL
                SELECT JC.JC_JS_FCLBookingOnlyLink AS JS_PK, JC.JC_PK AS sort_key
                FROM dbo.JobOrderLine AS JO
                JOIN dbo.JobSupplierBookingLine AS JSL ON JSL.JSL_JO_OrderLine = JO.JO_PK AND JSL.JSL_IsValid = 1
                JOIN dbo.JobContainer AS JC ON JC.JC_JSB_SupplierBooking = JSL.JSL_JSB_Booking AND JC.JC_IsValid = 1
                WHERE JO.JO_JD = JD.JD_PK
                  AND JO.JO_IsValid = 1
                  AND JC.JC_JS_FCLBookingOnlyLink IS NOT NULL
            ) AS LinkRows
            ORDER BY LinkRows.sort_key
        ) AS LinkedShipment
        ORDER BY COALESCE(JD.JD_SystemLastEditTimeUtc, JD.JD_SystemCreateTimeUtc) DESC, JD.JD_PK DESC
        OFFSET {offset} ROWS FETCH NEXT {sql_limit} ROWS ONLY;"""
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, po_number, shipment_id, view_as)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": {"obj_list": obj_list[:limit], "has_next_page": len(obj_list) > limit}}

@router.get("/myshipment/my-purchase-orders-line-items")
async def func_api_myshipment_my_purchase_order_lines(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("po_id", "str", 1, None, None), ("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer")])
    po_id = str(oq.get("po_id") or "").strip()
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @po_id uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @view_as nvarchar(40) = ?;

        WITH """ + helper_sql_visible_shipments_owned(name='visible_shipments') + """,
        visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.cvw_JobShipmentOrgs AS JSO ON JSO.JS_PK = JD.JD_JS
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_PK = @po_id
              AND JD.JD_IsValid = 1
              AND (
                    -- Controlling-customer view: the buyer on the PO is the logged-in org
                    BuyerOA.OA_OH = @org
                 OR JD.JD_JS IN (SELECT JS_PK FROM visible_shipments)
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobPackLines AS JLVisible ON JLVisible.JL_JSL_BookingLine = JSLVisible.JSL_PK AND JLVisible.JL_IsValid = 1
                        JOIN visible_shipments AS VSVisible ON VSVisible.JS_PK = JLVisible.JL_JS
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobContainer AS JCVisible ON JCVisible.JC_JSB_SupplierBooking = JSLVisible.JSL_JSB_Booking AND JCVisible.JC_IsValid = 1
                        JOIN visible_shipments AS VSVisible ON VSVisible.JS_PK = JCVisible.JC_JS_FCLBookingOnlyLink
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR (
                        @view_as = 'all'
                    AND (
                           JSO.ControllingCustomer_PK = @org
                        OR BuyerOA.OA_OH = @org
                        OR SupplierOA.OA_OH = @org
                        OR JD.JD_OH_Carrier = @org
                        OR JD.JD_OH_SendingAgent = @org
                        OR JD.JD_OH_ReceivingAgent = @org
                        OR EXISTS (
                            SELECT 1 FROM dbo.JobOrderLine AS JO
                            WHERE JO.JO_JD = JD.JD_PK AND JO.JO_IsValid = 1 AND JO.JO_OH_Supplier = @org
                        )
                    )
                 )
              )
        )
        SELECT
            CONVERT(varchar(36), JO.JO_PK) AS line_id,
            JO.JO_LineNo AS line_number,
            JO.JO_SubLineNo AS sub_line_number,
            JO.JO_Partno AS part_number,
            JO.JO_Description AS description,
            JO.JO_Quantity AS quantity,
            JO.JO_OuterPacks AS pack_quantity,
            COALESCE(NULLIF(JO.JO_OrderUnitOfQty, ''), NULLIF(JO.JO_F3_NKPackType, ''), NULLIF(JO.JO_OuterPacksUQ, ''), NULLIF(JO.JO_InnerPacksUQ, '')) AS pack_type,
            JO.JO_ItemPrice AS unit_price,
            JO.JO_LinePrice AS total_price,
            JO.JO_ActualWeight AS actual_weight,
            JO.JO_ActualVolume AS actual_volume
        FROM dbo.JobOrderLine AS JO
        JOIN visible_orders AS VO ON VO.JD_PK = JO.JO_JD
        WHERE JO.JO_IsValid = 1
        ORDER BY JO.JO_LineNo ASC, JO.JO_SubLineNo ASC, JO.JO_LineSplitNumber ASC, JO.JO_SystemCreateTimeUtc ASC;
    """
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, po_id, view_as)
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
        else:
            obj_list = []
    return {"status": 1, "message": jsonable_encoder(obj_list)}

@router.get("/myshipment/my-shipments")
async def func_api_myshipment_my_shipments(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    import re as _re
    def _safe_list(raw): return [v.strip() for v in str(raw or "").split(",") if v.strip() and _re.match(r'^[A-Za-z0-9\-_/ ]+$', v.strip())]
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("shipment_search", "str", 0, None, ""), ("shipment_id", "str", 0, None, ""), ("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer"), ("mode", "str", 0, None, ""), ("packing", "str", 0, None, ""), ("origin", "str", 0, None, ""), ("destination", "str", 0, None, ""), ("country", "str", 0, None, ""), ("inco", "str", 0, None, ""), ("carrier", "str", 0, None, ""), ("supplier_id", "str", 0, None, ""), ("period_days", "int", 0, None, 0)])
    limit = int(oq["limit"] or app_state.config_sql_read_limit_default)
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    limit = max(1, limit)
    page = max(1, int(oq["page"] or 1))
    shipment_search = str(oq.get("shipment_search") or "").strip()
    shipment_id = str(oq.get("shipment_id") or "").strip()
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    period_days = max(0, int(oq.get("period_days") or 0))
    mode_list = _safe_list(oq.get("mode"))
    packing_list = _safe_list(oq.get("packing"))
    origin_list = _safe_list(oq.get("origin"))
    dest_list = _safe_list(oq.get("destination"))
    country_list = [v.strip().upper() for v in str(oq.get("country") or "").split(",") if _re.match(r'^[A-Za-z]{2,3}$', v.strip())]
    inco_list = _safe_list(oq.get("inco"))
    # carrier and supplier_id are UUIDs
    _uuid_re = r'^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$'
    carrier_list = [v.strip() for v in str(oq.get("carrier") or "").split(",") if _re.match(_uuid_re, v.strip())]
    supplier_id_list = [v.strip() for v in str(oq.get("supplier_id") or "").split(",") if _re.match(_uuid_re, v.strip())]
    # Build parameterised WHERE clauses
    where_parts, filter_params = [], []
    def _add_in(col, lst):
        if lst:
            where_parts.append(f"{col} IN ({','.join(['?' for _ in lst])})")
            filter_params.extend(lst)
    _add_in("JS.JS_TransportMode", mode_list)
    _add_in("JS.JS_PackingMode", packing_list)
    _add_in("JS.JS_RL_NKOrigin", origin_list)
    _add_in("JS.JS_RL_NKDestination", dest_list)
    if country_list:
        where_parts.append(f"""EXISTS (
            SELECT 1
            FROM dbo.RefUNLOCO RL
            WHERE RL.RL_Code IN (JS.JS_RL_NKOrigin, JS.JS_RL_NKDestination)
              AND RL.RL_RN_NKCountryCode IN ({','.join(['?' for _ in country_list])})
        )""")
        filter_params.extend(country_list)
    _add_in("JS.JS_INCO", inco_list)
    if carrier_list:
        where_parts.append(f"EXISTS (SELECT 1 FROM dbo.OrgAddress OA2 JOIN dbo.OrgHeader OH2 ON OH2.OH_PK=OA2.OA_OH WHERE OA2.OA_PK=JS.JS_OA_BookedShippingLineAddress AND OH2.OH_PK IN ({','.join(['?' for _ in carrier_list])}))")
        filter_params.extend(carrier_list)
    if supplier_id_list:
        where_parts.append(f"EXISTS (SELECT 1 FROM dbo.cvw_JobShipmentOrgs JSO2 WHERE JSO2.JS_PK=JS.JS_PK AND JSO2.ControllingCustomer_PK IN ({','.join(['?' for _ in supplier_id_list])}))")
        filter_params.extend(supplier_id_list)
    if period_days > 0:
        where_parts.append(f"JS.JS_E_DEP >= DATEADD(day, -{period_days}, SYSUTCDATETIME())")
    extra_where = ("        WHERE " + "\n          AND ".join(where_parts)) if where_parts else ""
    offset = (page - 1) * limit
    sql_limit = limit + 1
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @shipment_search nvarchar(max) = ?;
        DECLARE @shipment_id_str nvarchar(max) = ?;
        DECLARE @view_as nvarchar(40) = ?;
        DECLARE @shipment_id uniqueidentifier = NULL;
        IF @shipment_id_str <> '' SET @shipment_id = TRY_CONVERT(uniqueidentifier, @shipment_id_str);
        WITH """ + helper_sql_visible_shipments(name='visible_shipments', with_shipment_id=True, with_declaration=True, with_search=True) + f"""
        SELECT
            CONVERT(varchar(36), JS.JS_PK) AS shipment_id,
            JS.JS_UniqueConsignRef AS shipment_reference,
            JS.JS_ShipmentStatus AS status,
            JS.JS_Phase AS phase,
            JS.JS_IsCancelled AS is_cancelled,
            JS.JS_IsBooking AS is_booking,
            JS.JS_BookingReference AS booking_reference,
            JS.JS_HouseBill AS house_bill,
            JS.JS_ConsolReference AS consol_reference,
            JS.JS_TransportMode AS transport_mode,
            JS.JS_PackingMode AS packing_mode,
            JS.JS_INCO AS inco_term,
            JS.JS_RL_NKOrigin AS origin,
            JS.JS_RL_NKDestination AS destination,
            JS.JS_E_DEP AS etd,
            JS.JS_E_ARV AS eta,
            JS.JS_ClientRequestedETA AS client_requested_eta,
            CAST(JS.JS_RevisedDeliveryDueDate AS datetime2) AS revised_delivery_due_date,
            CAST(JS.JS_DeliveryDueDate AS datetime2) AS delivery_due_date,
            JS.JS_GoodsDescription AS goods_description,
            JS.JS_TotalPackageCount AS package_count,
            JS.JS_DocumentedWeight AS documented_weight,
            JS.JS_DocumentedVolume AS documented_volume,
            JS.JS_DocumentedChargeable AS documented_chargeable,
            JH.JH_JobNum AS job_number,
            Summary.arrival_status,
            JS.JS_SystemCreateTimeUtc AS created_at,
            JS.JS_SystemLastEditTimeUtc AS updated_at
        FROM visible_shipments AS VS
        JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
        OUTER APPLY (
            SELECT TOP 1 JH.JH_JobNum
            FROM dbo.JobHeader AS JH
            WHERE JH.JH_ParentID = JS.JS_PK
              AND JH.JH_ParentTableCode = 'JS'
            ORDER BY JH.JH_SystemLastEditTimeUtc DESC
        ) AS JH
        OUTER APPLY (
            SELECT
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM dbo.StmALog AS ALArrival
                        LEFT JOIN dbo.StmEvent AS SEArrival ON SEArrival.SE_Code = ALArrival.SL_SE_NKEvent
                        WHERE ALArrival.SL_Table = 'JobShipment'
                          AND ALArrival.SL_Parent = JS.JS_PK
                          AND ALArrival.SL_EventTime IS NOT NULL
                          AND ISNULL(ALArrival.SL_IsCancelled, 'N') <> 'Y'
                          AND ISNULL(ALArrival.SL_IsEstimate, 'N') <> 'Y'
                          AND (
                                LOWER(COALESCE(SEArrival.SE_Desc, '')) LIKE '%arrival%'
                             OR LOWER(COALESCE(SEArrival.SE_Desc, '')) LIKE '%arrived%'
                             OR LOWER(COALESCE(ALArrival.SL_SE_NKEvent, '')) LIKE '%arv%'
                          )
                    ) THEN 'Arrived'
                    WHEN JS.JS_E_ARV IS NOT NULL THEN 'In Transit'
                    ELSE 'Arrival Pending'
                END AS arrival_status
        ) AS Summary
        {extra_where}
        ORDER BY COALESCE(JS.JS_SystemLastEditTimeUtc, JS.JS_SystemCreateTimeUtc) DESC, JS.JS_PK DESC
        OFFSET {offset} ROWS FETCH NEXT {sql_limit} ROWS ONLY;"""
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, shipment_search, shipment_id, view_as, *filter_params)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": {"obj_list": obj_list[:limit], "has_next_page": len(obj_list) > limit}}

@router.get("/myshipment/my-cache")
async def func_api_myshipment_my_cache(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer")])
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @view_as nvarchar(40) = ?;
        WITH {helper_sql_visible_shipments_owned(name='visible_shipments')}
        SELECT
            (SELECT TOP (10000) v FROM (SELECT DISTINCT JS.JS_TransportMode AS v FROM dbo.JobShipment JS JOIN visible_shipments VS ON VS.JS_PK=JS.JS_PK WHERE JS.JS_TransportMode IS NOT NULL AND JS.JS_TransportMode<>'') x FOR JSON PATH) AS mode_json,
            (SELECT TOP (10000) v FROM (SELECT DISTINCT JS.JS_PackingMode   AS v FROM dbo.JobShipment JS JOIN visible_shipments VS ON VS.JS_PK=JS.JS_PK WHERE JS.JS_PackingMode IS NOT NULL AND JS.JS_PackingMode<>'')   x FOR JSON PATH) AS packing_json,
            (SELECT TOP (10000) v FROM (SELECT DISTINCT JS.JS_RL_NKOrigin   AS v FROM dbo.JobShipment JS JOIN visible_shipments VS ON VS.JS_PK=JS.JS_PK WHERE JS.JS_RL_NKOrigin IS NOT NULL AND JS.JS_RL_NKOrigin<>'')   x FOR JSON PATH) AS origin_json,
            (SELECT TOP (10000) v FROM (SELECT DISTINCT JS.JS_RL_NKDestination AS v FROM dbo.JobShipment JS JOIN visible_shipments VS ON VS.JS_PK=JS.JS_PK WHERE JS.JS_RL_NKDestination IS NOT NULL AND JS.JS_RL_NKDestination<>'') x FOR JSON PATH) AS destination_json,
            (SELECT TOP (10000) id, name FROM (
                SELECT DISTINCT RL.RL_RN_NKCountryCode AS id, COALESCE(RN.RN_Desc, RL.RL_RN_NKCountryCode) AS name
                FROM dbo.JobShipment JS
                JOIN visible_shipments VS ON VS.JS_PK=JS.JS_PK
                JOIN dbo.RefUNLOCO RL ON RL.RL_Code IN (JS.JS_RL_NKOrigin, JS.JS_RL_NKDestination)
                LEFT JOIN dbo.RefCountry RN ON RN.RN_Code=RL.RL_RN_NKCountryCode
                WHERE RL.RL_RN_NKCountryCode IS NOT NULL AND RL.RL_RN_NKCountryCode<>''
            ) x ORDER BY name FOR JSON PATH) AS country_json,
            (SELECT TOP (10000) v FROM (SELECT DISTINCT JS.JS_INCO AS v FROM dbo.JobShipment JS JOIN visible_shipments VS ON VS.JS_PK=JS.JS_PK WHERE JS.JS_INCO IS NOT NULL AND JS.JS_INCO<>'') x FOR JSON PATH) AS inco_json,
            (SELECT TOP (10000) id, name FROM (SELECT DISTINCT CONVERT(varchar(36),OH.OH_PK) AS id, OH.OH_FullName AS name FROM dbo.JobShipment JS JOIN visible_shipments VS ON VS.JS_PK=JS.JS_PK JOIN dbo.OrgAddress OA ON OA.OA_PK=JS.JS_OA_BookedShippingLineAddress JOIN dbo.OrgHeader OH ON OH.OH_PK=OA.OA_OH WHERE OH.OH_FullName IS NOT NULL) x ORDER BY name FOR JSON PATH) AS carrier_json,
            (SELECT TOP (10000) id, name FROM (SELECT DISTINCT CONVERT(varchar(36),OH.OH_PK) AS id, OH.OH_FullName AS name FROM dbo.JobShipment JS JOIN visible_shipments VS ON VS.JS_PK=JS.JS_PK JOIN dbo.cvw_JobShipmentOrgs JSO ON JSO.JS_PK=JS.JS_PK JOIN dbo.OrgHeader OH ON OH.OH_PK=JSO.ControllingCustomer_PK WHERE OH.OH_FullName IS NOT NULL) x ORDER BY name FOR JSON PATH) AS supplier_json;"""
    import json as _json
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, view_as)
        row = await cursor.fetchone()
    def _parse(raw):
        if not raw: return []
        data = _json.loads(raw)
        if data and len(data[0]) == 1:
            key = list(data[0].keys())[0]
            return sorted([r[key] for r in data if r.get(key)])
        return data
    filter_options = {
        "mode":        _parse(row[0]),
        "packing":     _parse(row[1]),
        "origin":      _parse(row[2]),
        "destination": _parse(row[3]),
        "country":     _parse(row[4]),
        "inco":        _parse(row[5]),
        "carrier":     _parse(row[6]),
        "supplier":    _parse(row[7]) if row[7] else [],
    }
    return {"status": 1, "message": {"version": "2", "filter_options": filter_options}}

@router.get("/myshipment/my-containers")
async def func_api_myshipment_my_containers(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("shipment_id", "str", 0, None, ""), ("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer")])
    limit = int(oq["limit"] or app_state.config_sql_read_limit_default)
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    limit = max(1, limit)
    page = max(1, int(oq["page"] or 1))
    shipment_id = str(oq.get("shipment_id") or "").strip()
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    offset = (page - 1) * limit
    sql_limit = limit + 1
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @shipment_id_str nvarchar(max) = ?;
        DECLARE @view_as nvarchar(40) = ?;
        DECLARE @shipment_id uniqueidentifier = NULL;
        IF @shipment_id_str <> '' SET @shipment_id = TRY_CONVERT(uniqueidentifier, @shipment_id_str);
        WITH """ + helper_sql_visible_shipments(name='visible_shipments') + f""",
        visible_containers AS (
            SELECT DISTINCT JC.JC_PK
            FROM dbo.JobContainer AS JC
            LEFT JOIN dbo.JobConShipLink AS JN ON JN.JN_JK = JC.JC_JK
            LEFT JOIN visible_shipments AS VS1 ON VS1.JS_PK = JC.JC_JS_FCLBookingOnlyLink
            LEFT JOIN visible_shipments AS VS2 ON VS2.JS_PK = JN.JN_JS
            WHERE JC.JC_IsValid = 1
              AND (
                    VS1.JS_PK IS NOT NULL
                 OR VS2.JS_PK IS NOT NULL
                 OR (@view_as = 'all' AND (JC.JC_OH_CFSClient = @org OR JC.JC_OH_ShippingLine = @org))
              )
              AND (
                    @shipment_id IS NULL
                 OR JC.JC_JS_FCLBookingOnlyLink = @shipment_id
                 OR JN.JN_JS = @shipment_id
              )
        )
        SELECT
            CONVERT(varchar(36), JC.JC_PK) AS container_id,
            JC.JC_ContainerNum AS container_number,
            JC.JC_ContainerMode AS container_mode,
            JC.JC_ContainerStatus AS status,
            JC.JC_ContainerJobID AS container_job_id,
            JC.JC_SealNum AS seal_number,
            JC.JC_AdditionalSealNum AS additional_seal_number,
            JC.JC_IsEmptyContainer AS is_empty,
            JC.JC_IsShipperOwned AS is_shipper_owned,
            JC.JC_GrossWeight AS gross_weight,
            JC.JC_GrossWeightUQ AS gross_weight_unit,
            JC.JC_GrossVolume AS gross_volume,
            JC.JC_GrossVolumeUQ AS gross_volume_unit,
            JC.JC_PackDate AS pack_date,
            JC.JC_FCLWharfGateIn AS fcl_wharf_gate_in,
            JC.JC_FCLOnBoardVessel AS fcl_on_board_vessel,
            JC.JC_FCLUnloadFromVessel AS fcl_unload_from_vessel,
            JC.JC_FCLAvailable AS fcl_available,
            JC.JC_FCLWharfGateOut AS fcl_wharf_gate_out,
            CONVERT(varchar(36), JS.JS_PK) AS shipment_id,
            JS.JS_UniqueConsignRef AS shipment_reference,
            JK.JK_UniqueConsignRef AS consol_reference,
            JC.JC_SystemCreateTimeUtc AS created_at,
            JC.JC_SystemLastEditTimeUtc AS updated_at
        FROM visible_containers AS VC
        JOIN dbo.JobContainer AS JC ON JC.JC_PK = VC.JC_PK
        LEFT JOIN dbo.JobConsol AS JK ON JK.JK_PK = JC.JC_JK
        OUTER APPLY (
            SELECT TOP 1 JS.*
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobConShipLink AS JN ON JN.JN_JS = JS.JS_PK
            WHERE JS.JS_PK = JC.JC_JS_FCLBookingOnlyLink
               OR JN.JN_JK = JC.JC_JK
            ORDER BY JS.JS_SystemLastEditTimeUtc DESC
        ) AS JS
        ORDER BY COALESCE(JC.JC_SystemLastEditTimeUtc, JC.JC_SystemCreateTimeUtc) DESC, JC.JC_PK DESC
        OFFSET {offset} ROWS FETCH NEXT {sql_limit} ROWS ONLY;"""
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, shipment_id, view_as)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": {"obj_list": obj_list[:limit], "has_next_page": len(obj_list) > limit}}

@router.get("/myshipment/my-tracking")
async def func_api_myshipment_my_tracking(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("shipment_id", "str", 0, None, ""), ("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer")])
    limit = int(oq["limit"] or app_state.config_sql_read_limit_default)
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    limit = max(1, limit)
    page = max(1, int(oq["page"] or 1))
    shipment_id = str(oq.get("shipment_id") or "").strip()
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    offset = (page - 1) * limit
    sql_limit = limit + 1
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @shipment_id_str nvarchar(max) = ?;
        DECLARE @view_as nvarchar(40) = ?;
        DECLARE @shipment_id uniqueidentifier = NULL;
        IF @shipment_id_str <> '' SET @shipment_id = TRY_CONVERT(uniqueidentifier, @shipment_id_str);
        WITH """ + helper_sql_visible_shipments(name='visible_shipments', with_shipment_id=True) + f"""
        SELECT
            CONVERT(varchar(36), JS.JS_PK) AS shipment_id,
            JS.JS_UniqueConsignRef AS shipment_reference,
            JS.JS_HouseBill AS house_bill,
            JS.JS_TransportMode AS transport_mode,
            JS.JS_RL_NKOrigin AS origin,
            JS.JS_RL_NKDestination AS destination,
            JS.JS_E_DEP AS etd,
            JS.JS_E_ARV AS eta,
            JS.JS_ShipmentStatus AS shipment_status,
            AL.SL_SE_NKEvent AS event_code,
            COALESCE(SE.SE_Desc, AL.SL_SE_NKEvent) AS event_name,
            AL.SL_Reference AS event_reference,
            AL.SL_IsEstimate AS is_estimate,
            AL.SL_IsCancelled AS is_cancelled,
            AL.SL_EventTime AS event_at,
            AL.SL_PostedTimeUtc AS posted_at,
            AL.SL_GS_NKUser AS user_code,
            CASE
                WHEN SE.SE_IsExceptionEvent = 1 THEN 'Exception'
                WHEN SE.SE_IsCustomsMilestone = 1 THEN 'Customs'
                WHEN SE.SE_IsOrderTrackingMilestone = 1 THEN 'Order'
                WHEN SE.SE_IsAirMilestone = 1 THEN 'Air'
                WHEN SE.SE_IsSeaMilestone = 1 THEN 'Sea'
                WHEN SE.SE_IsRoadMilestone = 1 THEN 'Road'
                WHEN SE.SE_IsRailMilestone = 1 THEN 'Rail'
                ELSE 'Operational'
            END AS event_category,
            SE.SE_DisplayOrder AS display_order
        FROM visible_shipments AS VS
        JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
        JOIN dbo.StmALog AS AL ON AL.SL_Table = 'JobShipment' AND AL.SL_Parent = JS.JS_PK
        LEFT JOIN dbo.StmEvent AS SE ON SE.SE_Code = AL.SL_SE_NKEvent
        WHERE AL.SL_EventTime IS NOT NULL
          AND ISNULL(AL.SL_IsCancelled, 'N') <> 'Y'
        ORDER BY AL.SL_EventTime DESC, AL.SL_PostedTimeUtc DESC, AL.SL_PK DESC
        OFFSET {offset} ROWS FETCH NEXT {sql_limit} ROWS ONLY;"""
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, shipment_id, view_as)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": {"obj_list": obj_list[:limit], "has_next_page": len(obj_list) > limit}}

@router.get("/myshipment/my-alerts")
async def func_api_myshipment_my_alerts(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer")])
    limit = int(oq["limit"] or app_state.config_sql_read_limit_default)
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    limit = max(1, limit)
    page = max(1, int(oq["page"] or 1))
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    offset = (page - 1) * limit
    sql_limit = limit + 1
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @view_as nvarchar(40) = ?;
        WITH """ + helper_sql_visible_shipments(name='visible_shipments') + f""",
        pending_shipments AS (
            SELECT VS.JS_PK
            FROM visible_shipments AS VS
            JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
            WHERE NOT EXISTS (
                SELECT 1
                FROM dbo.StmALog AS ALArrival
                LEFT JOIN dbo.StmEvent AS SEArrival ON SEArrival.SE_Code = ALArrival.SL_SE_NKEvent
                WHERE ALArrival.SL_Table = 'JobShipment'
                  AND ALArrival.SL_Parent = JS.JS_PK
                  AND ALArrival.SL_EventTime IS NOT NULL
                  AND ISNULL(ALArrival.SL_IsCancelled, 'N') <> 'Y'
                  AND ISNULL(ALArrival.SL_IsEstimate, 'N') <> 'Y'
                  AND (
                        LOWER(COALESCE(SEArrival.SE_Desc, '')) LIKE '%arrival%'
                     OR LOWER(COALESCE(SEArrival.SE_Desc, '')) LIKE '%arrived%'
                     OR LOWER(COALESCE(ALArrival.SL_SE_NKEvent, '')) LIKE '%arv%'
                  )
            )
        ),
        exception_rows AS (
            SELECT
                'Shipment' AS source_type,
                CONVERT(varchar(36), JS.JS_PK) AS source_id,
                JS.JS_UniqueConsignRef AS reference,
                'Shipment Cancelled' AS exception_type,
                'High' AS severity,
                JS.JS_ShipmentStatus AS status,
                JS.JS_SystemLastEditTimeUtc AS event_at,
                'Shipment is marked cancelled.' AS note
            FROM pending_shipments AS PS
            JOIN dbo.JobShipment AS JS ON JS.JS_PK = PS.JS_PK
            WHERE JS.JS_IsCancelled = 1
            UNION ALL
            SELECT
                'Shipment',
                CONVERT(varchar(36), JS.JS_PK),
                JS.JS_UniqueConsignRef,
                'ETA Overdue',
                'Medium',
                JS.JS_ShipmentStatus,
                JS.JS_E_ARV,
                'Estimated arrival date has passed.'
            FROM pending_shipments AS PS
            JOIN dbo.JobShipment AS JS ON JS.JS_PK = PS.JS_PK
            WHERE JS.JS_IsCancelled = 0
              AND JS.JS_ShipmentStatus NOT IN ('CLS', 'FIN', 'DEL', 'COM')
              AND JS.JS_E_ARV IS NOT NULL
              AND JS.JS_E_ARV < SYSUTCDATETIME()
            UNION ALL
            SELECT
                'Shipment',
                CONVERT(varchar(36), JS.JS_PK),
                JS.JS_UniqueConsignRef,
                'Screening Review',
                'Medium',
                JS.JS_ScreeningStatus,
                JS.JS_SystemLastEditTimeUtc,
                'Screening status requires review.'
            FROM pending_shipments AS PS
            JOIN dbo.JobShipment AS JS ON JS.JS_PK = PS.JS_PK
            WHERE JS.JS_ScreeningStatus IS NOT NULL
              AND JS.JS_ScreeningStatus NOT IN ('', 'NOT')
        )
        SELECT *
        FROM exception_rows
        ORDER BY event_at DESC, source_id DESC
        OFFSET {offset} ROWS FETCH NEXT {sql_limit} ROWS ONLY;"""
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, view_as)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": {"obj_list": obj_list[:limit], "has_next_page": len(obj_list) > limit}}

@router.get("/myshipment/my-documents")
async def func_api_myshipment_my_documents(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("shipment_id", "str", 0, None, ""), ("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer")])
    limit = int(oq["limit"] or app_state.config_sql_read_limit_default)
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    limit = max(1, limit)
    page = max(1, int(oq["page"] or 1))
    shipment_id = str(oq.get("shipment_id") or "").strip()
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    offset = (page - 1) * limit
    sql_limit = limit + 1
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @shipment_id_str nvarchar(max) = ?;
        DECLARE @view_as nvarchar(40) = ?;
        DECLARE @shipment_id uniqueidentifier = NULL;
        IF @shipment_id_str <> '' SET @shipment_id = TRY_CONVERT(uniqueidentifier, @shipment_id_str);
        WITH """ + helper_sql_visible_shipments_owned(name='visible_shipments_for_orders') + f""",
        visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.cvw_JobShipmentOrgs AS JSO ON JSO.JS_PK = JD.JD_JS
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              AND (
                    -- Controlling-customer view: the buyer on the PO is the logged-in org
                    BuyerOA.OA_OH = @org
                 OR JD.JD_JS IN (SELECT JS_PK FROM visible_shipments_for_orders)
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobPackLines AS JLVisible ON JLVisible.JL_JSL_BookingLine = JSLVisible.JSL_PK AND JLVisible.JL_IsValid = 1
                        JOIN visible_shipments_for_orders AS VSVisible ON VSVisible.JS_PK = JLVisible.JL_JS
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobContainer AS JCVisible ON JCVisible.JC_JSB_SupplierBooking = JSLVisible.JSL_JSB_Booking AND JCVisible.JC_IsValid = 1
                        JOIN visible_shipments_for_orders AS VSVisible ON VSVisible.JS_PK = JCVisible.JC_JS_FCLBookingOnlyLink
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR (
                        @view_as = 'all'
                    AND (
                           JSO.ControllingCustomer_PK = @org
                        OR BuyerOA.OA_OH = @org
                        OR SupplierOA.OA_OH = @org
                        OR JD.JD_OH_Carrier = @org
                        OR JD.JD_OH_SendingAgent = @org
                        OR JD.JD_OH_ReceivingAgent = @org
                    )
                 )
              )
        ),
        """ + helper_sql_visible_shipments(name='visible_shipments') + f""",
        visible_consols AS (
            SELECT DISTINCT JN.JN_JK
            FROM dbo.JobConShipLink AS JN
            JOIN visible_shipments AS VS ON VS.JS_PK = JN.JN_JS
            WHERE JN.JN_JK IS NOT NULL
        ),
        document_rows AS (
            SELECT
                CONVERT(varchar(36), EQ.EQ_PK) AS document_id,
                'Required Document' AS document_source,
                EQ.EQ_ParentTableCode AS parent_type,
                CONVERT(varchar(36), EQ.EQ_ParentID) AS parent_id,
                EQ.EQ_DocCategory AS category,
                EQ.EQ_DocType AS document_type,
                EQ.EQ_DocUsage AS usage,
                EQ.EQ_DocDescription AS name,
                EQ.EQ_DocNumber AS document_number,
                CAST(EQ.EQ_DateRequired AS datetime2) AS date_required,
                CAST(EQ.EQ_DateReceived AS datetime2) AS date_received,
                EQ.EQ_ValidToDate AS valid_to,
                OwnerOH.OH_FullName AS owner_name,
                IssuedByOH.OH_FullName AS issued_by_name,
                EQ.EQ_SystemLastEditTimeUtc AS updated_at,
                0 AS has_file
            FROM dbo.JobRequiredDocument AS EQ
            LEFT JOIN dbo.OrgHeader AS OwnerOH ON OwnerOH.OH_PK = EQ.EQ_OH_DocumentOwner
            LEFT JOIN dbo.OrgHeader AS IssuedByOH ON IssuedByOH.OH_PK = EQ.EQ_OH_IssuedBy
            LEFT JOIN visible_orders AS VO ON EQ.EQ_ParentTableCode = 'JD' AND VO.JD_PK = EQ.EQ_ParentID
            LEFT JOIN visible_shipments AS VS ON EQ.EQ_ParentTableCode = 'JS' AND VS.JS_PK = EQ.EQ_ParentID
            LEFT JOIN visible_consols AS VC ON EQ.EQ_ParentTableCode = 'JK' AND VC.JN_JK = EQ.EQ_ParentID
            WHERE EQ.EQ_IsValid = 1
              AND (
                    VO.JD_PK IS NOT NULL
                 OR VS.JS_PK IS NOT NULL
                 OR VC.JN_JK IS NOT NULL
                 OR (@view_as = 'all' AND (EQ.EQ_OH_DocumentOwner = @org OR EQ.EQ_OH_IssuedBy = @org))
              )
              AND (
                    @shipment_id IS NULL
                 OR (EQ.EQ_ParentTableCode = 'JS' AND EQ.EQ_ParentID = @shipment_id)
                 OR (EQ.EQ_ParentTableCode = 'JD' AND EQ.EQ_ParentID IN (
                        SELECT JD_PK FROM dbo.JobOrderHeader WHERE JD_IsValid = 1 AND JD_JS = @shipment_id
                        UNION
                        SELECT JDLink.JD_PK
                        FROM dbo.JobOrderHeader AS JDLink
                        JOIN dbo.JobOrderLine AS JOLink ON JOLink.JO_JD = JDLink.JD_PK AND JOLink.JO_IsValid = 1
                        JOIN dbo.JobSupplierBookingLine AS JSLLink ON JSLLink.JSL_JO_OrderLine = JOLink.JO_PK AND JSLLink.JSL_IsValid = 1
                        JOIN dbo.JobPackLines AS JLLink ON JLLink.JL_JSL_BookingLine = JSLLink.JSL_PK AND JLLink.JL_IsValid = 1
                        WHERE JDLink.JD_IsValid = 1 AND JLLink.JL_JS = @shipment_id
                        UNION
                        SELECT JDLink.JD_PK
                        FROM dbo.JobOrderHeader AS JDLink
                        JOIN dbo.JobOrderLine AS JOLink ON JOLink.JO_JD = JDLink.JD_PK AND JOLink.JO_IsValid = 1
                        JOIN dbo.JobSupplierBookingLine AS JSLLink ON JSLLink.JSL_JO_OrderLine = JOLink.JO_PK AND JSLLink.JSL_IsValid = 1
                        JOIN dbo.JobContainer AS JCLink ON JCLink.JC_JSB_SupplierBooking = JSLLink.JSL_JSB_Booking AND JCLink.JC_IsValid = 1
                        WHERE JDLink.JD_IsValid = 1 AND JCLink.JC_JS_FCLBookingOnlyLink = @shipment_id
                    ))
                 OR (EQ.EQ_ParentTableCode = 'JK' AND EQ.EQ_ParentID IN (SELECT JN_JK FROM dbo.JobConShipLink WHERE JN_JS = @shipment_id))
              )
            UNION ALL
            SELECT
                CONVERT(varchar(36), JDD.JDD_PK),
                'Job Document',
                JDD.JDD_ParentTableCode,
                CONVERT(varchar(36), JDD.JDD_ParentID),
                NULL,
                NULL,
                NULL,
                JDD.JDD_Name,
                NULL,
                NULL,
                JDD.JDD_SystemCreateTimeUtc,
                NULL,
                NULL,
                NULL,
                JDD.JDD_SystemLastEditTimeUtc,
                0
            FROM dbo.JobDocumentData AS JDD
            LEFT JOIN visible_orders AS VO ON JDD.JDD_ParentTableCode = 'JD' AND VO.JD_PK = JDD.JDD_ParentID
            LEFT JOIN visible_shipments AS VS ON JDD.JDD_ParentTableCode = 'JS' AND VS.JS_PK = JDD.JDD_ParentID
            LEFT JOIN visible_consols AS VC ON JDD.JDD_ParentTableCode = 'JK' AND VC.JN_JK = JDD.JDD_ParentID
            WHERE (
                    VO.JD_PK IS NOT NULL
                 OR VS.JS_PK IS NOT NULL
                 OR VC.JN_JK IS NOT NULL
              )
              AND (
                    @shipment_id IS NULL
                 OR (JDD.JDD_ParentTableCode = 'JD' AND JDD.JDD_ParentID IN (
                        SELECT JD_PK FROM dbo.JobOrderHeader WHERE JD_IsValid = 1 AND JD_JS = @shipment_id
                        UNION
                        SELECT JDLink.JD_PK
                        FROM dbo.JobOrderHeader AS JDLink
                        JOIN dbo.JobOrderLine AS JOLink ON JOLink.JO_JD = JDLink.JD_PK AND JOLink.JO_IsValid = 1
                        JOIN dbo.JobSupplierBookingLine AS JSLLink ON JSLLink.JSL_JO_OrderLine = JOLink.JO_PK AND JSLLink.JSL_IsValid = 1
                        JOIN dbo.JobPackLines AS JLLink ON JLLink.JL_JSL_BookingLine = JSLLink.JSL_PK AND JLLink.JL_IsValid = 1
                        WHERE JDLink.JD_IsValid = 1 AND JLLink.JL_JS = @shipment_id
                        UNION
                        SELECT JDLink.JD_PK
                        FROM dbo.JobOrderHeader AS JDLink
                        JOIN dbo.JobOrderLine AS JOLink ON JOLink.JO_JD = JDLink.JD_PK AND JOLink.JO_IsValid = 1
                        JOIN dbo.JobSupplierBookingLine AS JSLLink ON JSLLink.JSL_JO_OrderLine = JOLink.JO_PK AND JSLLink.JSL_IsValid = 1
                        JOIN dbo.JobContainer AS JCLink ON JCLink.JC_JSB_SupplierBooking = JSLLink.JSL_JSB_Booking AND JCLink.JC_IsValid = 1
                        WHERE JDLink.JD_IsValid = 1 AND JCLink.JC_JS_FCLBookingOnlyLink = @shipment_id
                    ))
                 OR (JDD.JDD_ParentTableCode = 'JS' AND JDD.JDD_ParentID = @shipment_id)
                 OR (JDD.JDD_ParentTableCode = 'JK' AND JDD.JDD_ParentID IN (SELECT JN_JK FROM dbo.JobConShipLink WHERE JN_JS = @shipment_id))
              )
        )
        SELECT *
        FROM document_rows
        ORDER BY updated_at DESC, document_id DESC
        OFFSET {offset} ROWS FETCH NEXT {sql_limit} ROWS ONLY;"""
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, shipment_id, view_as)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": {"obj_list": obj_list[:limit], "has_next_page": len(obj_list) > limit}}

@router.get("/myshipment/my-documents-download")
async def func_api_myshipment_my_documents_download(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("document_id", "str", 1, None, None)])
    raise Exception("Document download is not available from JobDocumentData in this CargoWise database. Document metadata can be viewed, but file storage mapping needs to be configured separately.")

@router.get("/myshipment/my-analytics")
async def func_api_myshipment_my_analytics(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("Organization id missing")
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("module", "str", 0, ["master", "purchase_orders", "shipments", "containers"], "master"), ("view_as", "str", 0, ["controlling_customer", "all"], "controlling_customer")])
    view_as = str(oq.get("view_as") or "controlling_customer").strip()
    kpis_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @view_as nvarchar(40) = ?;
        WITH """ + helper_sql_visible_shipments_owned(name='visible_shipments_for_orders') + """,
        visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.cvw_JobShipmentOrgs AS JSO ON JSO.JS_PK = JD.JD_JS
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              AND (
                    -- Controlling-customer view: the buyer on the PO is the logged-in org
                    BuyerOA.OA_OH = @org
                 OR JD.JD_JS IN (SELECT JS_PK FROM visible_shipments_for_orders)
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobPackLines AS JLVisible ON JLVisible.JL_JSL_BookingLine = JSLVisible.JSL_PK AND JLVisible.JL_IsValid = 1
                        JOIN visible_shipments_for_orders AS VSVisible ON VSVisible.JS_PK = JLVisible.JL_JS
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobContainer AS JCVisible ON JCVisible.JC_JSB_SupplierBooking = JSLVisible.JSL_JSB_Booking AND JCVisible.JC_IsValid = 1
                        JOIN visible_shipments_for_orders AS VSVisible ON VSVisible.JS_PK = JCVisible.JC_JS_FCLBookingOnlyLink
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR (
                        @view_as = 'all'
                    AND (
                           JSO.ControllingCustomer_PK = @org
                        OR BuyerOA.OA_OH = @org
                        OR SupplierOA.OA_OH = @org
                        OR JD.JD_OH_Carrier = @org
                        OR JD.JD_OH_SendingAgent = @org
                        OR JD.JD_OH_ReceivingAgent = @org
                        OR EXISTS (
                            SELECT 1
                            FROM dbo.JobOrderLine AS JO
                            WHERE JO.JO_JD = JD.JD_PK
                              AND JO.JO_IsValid = 1
                              AND JO.JO_OH_Supplier = @org
                        )
                    )
                 )
              )
        ),
        """ + helper_sql_visible_shipments(name='visible_shipments') + """,
        visible_containers AS (
            SELECT DISTINCT JC.JC_PK
            FROM dbo.JobContainer AS JC
            LEFT JOIN dbo.JobConShipLink AS JN ON JN.JN_JK = JC.JC_JK
            LEFT JOIN visible_shipments AS VS1 ON VS1.JS_PK = JC.JC_JS_FCLBookingOnlyLink
            LEFT JOIN visible_shipments AS VS2 ON VS2.JS_PK = JN.JN_JS
            WHERE JC.JC_IsValid = 1
              AND (
                    VS1.JS_PK IS NOT NULL
                 OR VS2.JS_PK IS NOT NULL
                 OR (@view_as = 'all' AND (JC.JC_OH_CFSClient = @org OR JC.JC_OH_ShippingLine = @org))
              )
        ),
        line_summary AS (
            SELECT JO.JO_JD AS order_pk, COUNT(1) AS line_count
            FROM dbo.JobOrderLine AS JO
            WHERE JO.JO_IsValid = 1
            GROUP BY JO.JO_JD
        )
        SELECT
            (SELECT COUNT(1) FROM visible_orders) AS purchase_orders,
            (SELECT COUNT(1) FROM visible_shipments) AS shipments,
            (SELECT COUNT(1) FROM visible_containers) AS containers,
            (SELECT COALESCE(SUM(LS.line_count), 0) FROM visible_orders AS VO JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK LEFT JOIN line_summary AS LS ON LS.order_pk = JD.JD_PK) AS purchase_order_lines,
            (SELECT COUNT(1) FROM visible_orders AS VO JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK WHERE JD.JD_IsReleased = 1) AS released_purchase_orders,
            (SELECT COUNT(1) FROM visible_orders AS VO JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK WHERE JD.JD_IsPriority = 1) AS priority_purchase_orders,
            (SELECT COUNT(1) FROM visible_orders AS VO JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK WHERE JD.JD_IsCancelled = 1) AS cancelled_purchase_orders,
            (SELECT COUNT(1) FROM visible_shipments AS VS JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK WHERE JS.JS_IsCancelled = 1) AS cancelled_shipments,
            (SELECT COUNT(1)
             FROM visible_shipments AS VS
             JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
             WHERE COALESCE(JS.JS_E_ARV, JS.JS_ClientRequestedETA, CAST(JS.JS_DeliveryDueDate AS datetime2), CAST(JS.JS_RevisedDeliveryDueDate AS datetime2)) >= SYSUTCDATETIME()
               AND COALESCE(JS.JS_E_ARV, JS.JS_ClientRequestedETA, CAST(JS.JS_DeliveryDueDate AS datetime2), CAST(JS.JS_RevisedDeliveryDueDate AS datetime2)) < DATEADD(day, 7, SYSUTCDATETIME())
               AND ISNULL(JS.JS_IsCancelled, 0) = 0) AS arriving_soon_shipments,
            (SELECT COUNT(1)
             FROM visible_shipments AS VS
             JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
             WHERE COALESCE(JS.JS_E_ARV, JS.JS_ClientRequestedETA, CAST(JS.JS_DeliveryDueDate AS datetime2), CAST(JS.JS_RevisedDeliveryDueDate AS datetime2)) < SYSUTCDATETIME()
               AND JS.JS_E_DEP > DATEADD(day, -45, SYSUTCDATETIME())
               AND JS.JS_E_DEP < SYSUTCDATETIME()
               AND ISNULL(JS.JS_IsCancelled, 0) = 0
               AND ISNULL(JS.JS_ShipmentStatus, '') NOT IN ('CLS', 'CMP', 'COM', 'FIN', 'DEL')) AS delayed_shipments;"""
    purchase_orders_by_status_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @view_as nvarchar(40) = ?;
        WITH """ + helper_sql_visible_shipments_owned(name='visible_shipments_for_orders') + """,
        visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.cvw_JobShipmentOrgs AS JSO ON JSO.JS_PK = JD.JD_JS
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              AND (
                    -- Controlling-customer view: the buyer on the PO is the logged-in org
                    BuyerOA.OA_OH = @org
                 OR JD.JD_JS IN (SELECT JS_PK FROM visible_shipments_for_orders)
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobPackLines AS JLVisible ON JLVisible.JL_JSL_BookingLine = JSLVisible.JSL_PK AND JLVisible.JL_IsValid = 1
                        JOIN visible_shipments_for_orders AS VSVisible ON VSVisible.JS_PK = JLVisible.JL_JS
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR EXISTS (
                        SELECT 1
                        FROM dbo.JobOrderLine AS JOVisible
                        JOIN dbo.JobSupplierBookingLine AS JSLVisible ON JSLVisible.JSL_JO_OrderLine = JOVisible.JO_PK AND JSLVisible.JSL_IsValid = 1
                        JOIN dbo.JobContainer AS JCVisible ON JCVisible.JC_JSB_SupplierBooking = JSLVisible.JSL_JSB_Booking AND JCVisible.JC_IsValid = 1
                        JOIN visible_shipments_for_orders AS VSVisible ON VSVisible.JS_PK = JCVisible.JC_JS_FCLBookingOnlyLink
                        WHERE JOVisible.JO_JD = JD.JD_PK
                          AND JOVisible.JO_IsValid = 1
                    )
                 OR (
                        @view_as = 'all'
                    AND (
                           JSO.ControllingCustomer_PK = @org
                        OR BuyerOA.OA_OH = @org
                        OR SupplierOA.OA_OH = @org
                        OR JD.JD_OH_Carrier = @org
                        OR JD.JD_OH_SendingAgent = @org
                        OR JD.JD_OH_ReceivingAgent = @org
                        OR EXISTS (
                            SELECT 1
                            FROM dbo.JobOrderLine AS JO
                            WHERE JO.JO_JD = JD.JD_PK
                              AND JO.JO_IsValid = 1
                              AND JO.JO_OH_Supplier = @org
                        )
                    )
                 )
              )
        )
        SELECT JD.JD_OrderStatus AS status, COUNT(1) AS count
        FROM visible_orders AS VO
        JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK
        GROUP BY JD.JD_OrderStatus
        ORDER BY COUNT(1) DESC;"""
    shipments_by_status_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @view_as nvarchar(40) = ?;
        WITH """ + helper_sql_visible_shipments(name='visible_shipments') + """
        SELECT JS.JS_ShipmentStatus AS status, COUNT(1) AS count
        FROM visible_shipments AS VS
        JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
        GROUP BY JS.JS_ShipmentStatus
        ORDER BY COUNT(1) DESC;"""
    shipments_by_month_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @view_as nvarchar(40) = ?;
        WITH """ + helper_sql_visible_shipments(name='visible_shipments') + """
        SELECT TOP 12
            FORMAT(JS.JS_SystemCreateTimeUtc, 'yyyy-MM') AS month,
            COUNT(1) AS count
        FROM visible_shipments AS VS
        JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
        WHERE JS.JS_SystemCreateTimeUtc IS NOT NULL
        GROUP BY FORMAT(JS.JS_SystemCreateTimeUtc, 'yyyy-MM')
        ORDER BY month DESC;"""
    transport_modes_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @view_as nvarchar(40) = ?;
        WITH """ + helper_sql_visible_shipments(name='visible_shipments') + """
        SELECT JS.JS_TransportMode AS transport_mode, COUNT(1) AS count
        FROM visible_shipments AS VS
        JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
        GROUP BY JS.JS_TransportMode
        ORDER BY COUNT(1) DESC;"""
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(kpis_sql, org_pk, view_as)
        kpis_columns = [column[0] for column in cursor.description]
        kpis = [dict(zip(kpis_columns, row)) for row in await cursor.fetchall()]
        purchase_orders_by_status, shipments_by_status, shipments_by_month, transport_modes = [], [], [], []
        if oq["module"] in ("master", "purchase_orders"):
            await cursor.execute(purchase_orders_by_status_sql, org_pk, view_as)
            purchase_orders_by_status_columns = [column[0] for column in cursor.description]
            purchase_orders_by_status = [dict(zip(purchase_orders_by_status_columns, row)) for row in await cursor.fetchall()]
        if oq["module"] == "purchase_orders":
            return {"status": 1, "message": jsonable_encoder({"kpis": kpis[0] if kpis else {}, "purchase_orders_by_status": purchase_orders_by_status})}
        if oq["module"] == "containers":
            return {"status": 1, "message": jsonable_encoder({"kpis": kpis[0] if kpis else {}})}
        if oq["module"] in ("master", "shipments"):
            await cursor.execute(shipments_by_status_sql, org_pk, view_as)
            shipments_by_status_columns = [column[0] for column in cursor.description]
            shipments_by_status = [dict(zip(shipments_by_status_columns, row)) for row in await cursor.fetchall()]
            await cursor.execute(shipments_by_month_sql, org_pk, view_as)
            shipments_by_month_columns = [column[0] for column in cursor.description]
            shipments_by_month = [dict(zip(shipments_by_month_columns, row)) for row in await cursor.fetchall()]
            await cursor.execute(transport_modes_sql, org_pk, view_as)
            transport_modes_columns = [column[0] for column in cursor.description]
            transport_modes = [dict(zip(transport_modes_columns, row)) for row in await cursor.fetchall()]
        if oq["module"] == "shipments":
            return {"status": 1, "message": jsonable_encoder({"kpis": kpis[0] if kpis else {}, "shipments_by_status": shipments_by_status, "shipments_by_month": shipments_by_month, "transport_modes": transport_modes})}
    analytics_object = {"kpis": kpis[0] if kpis else {}, "purchase_orders_by_status": purchase_orders_by_status, "shipments_by_status": shipments_by_status, "shipments_by_month": shipments_by_month, "transport_modes": transport_modes}
    return {"status": 1, "message": jsonable_encoder(analytics_object)}

@router.get("/myshipment/buyer-360")
async def func_api_myshipment_buyer_360(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mssql_read_fallback: raise Exception("MSSQL client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("org_id", "str", 1, None, None)])
    org_id = str(oq.get("org_id") or "").strip()
    sql = """
        SET NOCOUNT ON;
        SELECT TOP 1
            CONVERT(varchar(36), OH.OH_PK) AS org_id,
            OH.OH_FullName AS name,
            OH.OH_Category AS category,
            OH.OH_IsActive AS is_active,
            OH.OH_IsValid AS is_valid,
            OH.OH_IsGlobalAccount AS is_global_account,
            OH.OH_IsConsignee AS is_consignee,
            OH.OH_IsConsignor AS is_consignor,
            OH.OH_RL_NKClosestPort AS closest_port,
            DefaultAddress.CountryCode AS country_code,
            DefaultAddress.State AS state,
            DefaultAddress.City AS city,
            DefaultAddress.Address1 AS address_1,
            DefaultAddress.Address2 AS address_2,
            DefaultAddress.PostCode AS post_code,
            OH.OH_ScreeningStatus AS screening_status,
            ISNULL(POs.TotalPOs, 0) AS total_purchase_orders,
            ISNULL(Shipments.TotalBookings, 0) AS total_bookings,
            ISNULL(Shipments.TotalShipments, 0) AS total_shipments,
            ISNULL(Consols.TotalConsols, 0) AS total_consols,
            ISNULL(Finance.TotalInvoices, 0) AS total_invoices,
            Shipments.LastActivityDate AS last_activity_date,
            OH.OH_SystemCreateUser AS created_by,
            CreateStaff.GS_FullName AS created_by_name,
            CASE WHEN OH.OH_SystemCreateTimeUtc IS NULL THEN NULL ELSE CONVERT(varchar(33), OH.OH_SystemCreateTimeUtc, 126) + 'Z' END AS created_at,
            OH.OH_SystemLastEditUser AS updated_by,
            UpdateStaff.GS_FullName AS updated_by_name,
            CASE WHEN OH.OH_SystemLastEditTimeUtc IS NULL THEN NULL ELSE CONVERT(varchar(33), OH.OH_SystemLastEditTimeUtc, 126) + 'Z' END AS updated_at
        FROM dbo.OrgHeader OH
        OUTER APPLY (
            SELECT TOP 1 
                OA.OA_RN_NKCountryCode AS CountryCode, 
                OA.OA_State AS State,
                OA.OA_City AS City,
                OA.OA_Address1 AS Address1,
                OA.OA_Address2 AS Address2,
                OA.OA_PostCode AS PostCode
            FROM dbo.OrgAddress OA
            WHERE OA.OA_OH = OH.OH_PK AND OA.OA_IsValid = 1
            ORDER BY OA.OA_SystemCreateTimeUtc ASC
        ) DefaultAddress
        OUTER APPLY (
            SELECT COUNT(JD.JD_PK) AS TotalPOs
            FROM dbo.JobOrderHeader JD
            INNER JOIN dbo.OrgAddress OA ON JD.JD_OA_BuyerAddress = OA.OA_PK
            WHERE OA.OA_OH = OH.OH_PK
        ) POs
        OUTER APPLY (
            SELECT
                COUNT(JS.JS_PK) AS TotalShipments,
                SUM(CASE WHEN JS.JS_IsBooking = 1 THEN 1 ELSE 0 END) AS TotalBookings,
                MAX(JS.JS_SystemCreateTimeUtc) AS LastActivityDate
            FROM dbo.JobShipment JS
            INNER JOIN dbo.cvw_JobShipmentOrgs JSO ON JS.JS_PK = JSO.JS_PK
            WHERE JSO.JS_E2_OA_OH_Consignee = OH.OH_PK
        ) Shipments
        OUTER APPLY (
            SELECT COUNT(JK.JK_PK) AS TotalConsols
            FROM dbo.JobConsol JK
            INNER JOIN dbo.OrgAddress OA ON JK.JK_OA_SendingForwarderAddress = OA.OA_PK
            WHERE OA.OA_OH = OH.OH_PK
        ) Consols
        OUTER APPLY (
            SELECT COUNT(AH.AH_PK) AS TotalInvoices
            FROM dbo.AccTransactionHeader AH
            WHERE AH.AH_OH = OH.OH_PK
        ) Finance
        LEFT JOIN dbo.GlbStaff CreateStaff ON CreateStaff.GS_Code = OH.OH_SystemCreateUser
        LEFT JOIN dbo.GlbStaff UpdateStaff ON UpdateStaff.GS_Code = OH.OH_SystemLastEditUser
        WHERE OH.OH_IsActive = 1 
          AND OH.OH_IsValid = 1 
          AND OH.OH_IsConsignee = 1
          AND OH.OH_PK = TRY_CONVERT(uniqueidentifier, ?)
        ORDER BY OH.OH_FullName ASC;"""
    async with app_state.client_mssql_read_fallback.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_id)
        columns = [column[0] for column in cursor.description]
        row = await cursor.fetchone()
    return {"status": 1, "message": dict(zip(columns, row)) if row else None}