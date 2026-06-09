# packages
from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder

# router
router = APIRouter()

# api
@router.get("/my/cargowise-profile")
async def func_api_my_cargowise_profile(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    role_map = {
        "is_consignee": "Consignee",
        "is_consignor": "Consignor",
        "is_transport_client": "Transport Client",
        "is_warehouse_client": "Warehouse Client",
        "is_forwarder": "Forwarder",
        "is_shipping_provider": "Shipping Provider",
        "is_broker": "Broker",
        "is_shipping_line": "Shipping Line",
        "is_controlling_customer": "Controlling Customer",
        "is_controlling_agent": "Controlling Agent",
    }
    async with app_state.client_mssql_read.acquire() as conn:
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
                OH.OH_SystemCreateTimeUtc AS created_at,
                OH.OH_SystemLastEditTimeUtc AS updated_at,
                OH.OH_IsConsignee AS is_consignee,
                OH.OH_IsConsignor AS is_consignor,
                OH.OH_IsTransportClient AS is_transport_client,
                OH.OH_IsWarehouseClient AS is_warehouse_client,
                OH.OH_IsForwarder AS is_forwarder,
                OH.OH_IsShippingProvider AS is_shipping_provider,
                OH.OH_IsBroker AS is_broker,
                OH.OH_IsShippingLine AS is_shipping_line,
                OH.OH_IsControllingCustomer AS is_controlling_customer,
                OH.OH_IsControllingAgent AS is_controlling_agent
            FROM dbo.OrgHeader AS OH
            WHERE OH.OH_PK = TRY_CONVERT(uniqueidentifier, ?);""", org_pk)
        org_columns = [column[0] for column in cursor.description]
        org_rows = [dict(zip(org_columns, row)) for row in await cursor.fetchall()]
        if not org_rows: raise Exception("CargoWise profile not found")
        org = org_rows[0]
        roles = [label for key, label in role_map.items() if org.pop(key, None)]
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
                OA.OA_Phone AS phone,
                OA.OA_Mobile AS mobile,
                OA.OA_Email AS email
            FROM dbo.OrgAddress AS OA
            WHERE OA.OA_OH = TRY_CONVERT(uniqueidentifier, ?)
              AND OA.OA_IsValid = 1
              AND OA.OA_IsActive = 1
            ORDER BY OA.OA_Code;""", org_pk)
        address_columns = [column[0] for column in cursor.description]
        addresses = [dict(zip(address_columns, row)) for row in await cursor.fetchall()]
        await cursor.execute("""
            SELECT TOP 50
                CONVERT(varchar(36), OC.OC_PK) AS contact_id,
                OC.OC_ContactName AS name,
                OC.OC_Title AS title,
                OC.OC_Phone AS phone,
                OC.OC_Mobile AS mobile,
                OC.OC_Email AS email,
                OC.OC_WebAccessEnabled AS web_access_enabled
            FROM dbo.OrgContact AS OC
            WHERE OC.OC_OH = TRY_CONVERT(uniqueidentifier, ?)
              AND OC.OC_IsValid = 1
              AND OC.OC_IsActive = 1
            ORDER BY OC.OC_ContactName;""", org_pk)
        contact_columns = [column[0] for column in cursor.description]
        contacts = [dict(zip(contact_columns, row)) for row in await cursor.fetchall()]
    profile_object = {"org": org, "roles": roles, "addresses": addresses, "contacts": contacts}
    return {"status": 1, "message": jsonable_encoder(profile_object)}

@router.get("/my/cargowise-purchase-orders")
async def func_api_my_cargowise_purchase_orders(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 50), ("page", "int", 0, None, 1), ("po_number", "str", 0, None, "")])
    limit = max(1, min(int(oq["limit"] or 50), 200))
    page = max(1, int(oq["page"] or 1))
    offset = (page - 1) * limit
    po_number = str(oq.get("po_number") or "").strip()
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @po_number nvarchar(max) = ?;
        WITH visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              { "AND JD.JD_OrderNumber = @po_number" if po_number else "" }
              AND (
                    BuyerOA.OA_OH = @org
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
            CONVERT(varchar(36), JS.JS_PK) AS shipment_id,
            JS.JS_UniqueConsignRef AS shipment_reference,
            JS.JS_ShipmentStatus AS shipment_status,
            COALESCE(LS.line_count, 0) AS line_count,
            LS.total_quantity,
            LS.total_value,
            LS.total_weight,
            LS.total_volume,
            JD.JD_SystemCreateTimeUtc AS created_at,
            JD.JD_SystemLastEditTimeUtc AS updated_at
        FROM visible_orders AS VO
        JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK
        LEFT JOIN dbo.JobShipment AS JS ON JS.JS_PK = JD.JD_JS
        LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
        LEFT JOIN dbo.OrgHeader AS BuyerOH ON BuyerOH.OH_PK = BuyerOA.OA_OH
        LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
        LEFT JOIN dbo.OrgHeader AS SupplierOH ON SupplierOH.OH_PK = SupplierOA.OA_OH
        LEFT JOIN line_summary AS LS ON LS.order_pk = JD.JD_PK
        ORDER BY COALESCE(JD.JD_SystemLastEditTimeUtc, JD.JD_SystemCreateTimeUtc) DESC
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY;"""
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, po_number)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": jsonable_encoder(obj_list)}

@router.get("/my/cargowise-purchase-orders/{po_id}/lines")
async def func_api_my_cargowise_purchase_order_lines(po_id: str, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("search", "str", 0, None, "")])
    search = str(oq.get("search") or "").strip()
    sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @po_id uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        DECLARE @search nvarchar(max) = ?;

        IF NOT EXISTS (
            SELECT 1 FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_PK = @po_id
              AND JD.JD_IsValid = 1
              AND (
                    BuyerOA.OA_OH = @org
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
        BEGIN
            SELECT TOP 0 1;
            RETURN;
        END

        SELECT
            CONVERT(varchar(36), JO.JO_PK) AS line_id,
            JO.JO_LineNumber AS line_number,
            JO.JO_PartNum AS part_number,
            JO.JO_Description AS description,
            JO.JO_Quantity AS quantity,
            JO.JO_PackQty AS pack_quantity,
            JO.JO_PackType AS pack_type,
            JO.JO_LinePrice AS unit_price,
            (JO.JO_LinePrice * JO.JO_Quantity) AS total_price,
            JO.JO_ActualWeight AS actual_weight,
            JO.JO_ActualVolume AS actual_volume
        FROM dbo.JobOrderLine AS JO
        WHERE JO.JO_JD = @po_id
          AND JO.JO_IsValid = 1
          AND (
                @search = ''
             OR LOWER(JO.JO_PartNum)     LIKE '%' + LOWER(@search) + '%'
             OR LOWER(JO.JO_Description) LIKE '%' + LOWER(@search) + '%'
          )
        ORDER BY JO.JO_LineNumber ASC, JO.JO_SystemCreateTimeUtc ASC;
    """
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk, po_id, search)
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
        else:
            obj_list = []
    return {"status": 1, "message": jsonable_encoder(obj_list)}

@router.get("/my/cargowise-shipments")
async def func_api_my_cargowise_shipments(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 50), ("page", "int", 0, None, 1)])
    limit = max(1, min(int(oq["limit"] or 50), 200))
    page = max(1, int(oq["page"] or 1))
    offset = (page - 1) * limit
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            LEFT JOIN dbo.JobDeclaration AS JE ON JE.JE_JS = JS.JS_PK AND JE.JE_IsValid = 1
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org
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
                 OR JD.JD_OH_ReceivingAgent = @org
                 OR JE.JE_OH_Importer = @org
                 OR JE.JE_OH_Supplier = @org
                 OR JE.JE_OH_Buyer = @org
                 OR JE.JE_OH_Consignee = @org
                 OR JE.JE_OH_Exporter = @org
                 OR JE.JE_OH_Forwarder = @org
                 OR JE.JE_OH_ControllingCustomer = @org
                 OR JE.JE_OH_ControllingAgent = @org
              )
        )
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
            Summary.linked_purchase_orders,
            Summary.container_count,
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
                (SELECT COUNT(JD_PK) FROM dbo.JobOrderHeader WHERE JD_JS = JS.JS_PK) AS linked_purchase_orders,
                (SELECT COUNT(DISTINCT JC.JC_PK) FROM dbo.JobContainer AS JC LEFT JOIN dbo.JobConShipLink AS JN ON JN.JN_JK = JC.JC_JK WHERE JC.JC_JS_FCLBookingOnlyLink = JS.JS_PK OR JN.JN_JS = JS.JS_PK) AS container_count
        ) AS Summary
        ORDER BY COALESCE(JS.JS_SystemLastEditTimeUtc, JS.JS_SystemCreateTimeUtc) DESC
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY;"""
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": jsonable_encoder(obj_list)}

@router.get("/my/cargowise-containers")
async def func_api_my_cargowise_containers(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 50), ("page", "int", 0, None, 1)])
    limit = max(1, min(int(oq["limit"] or 50), 200))
    page = max(1, int(oq["page"] or 1))
    offset = (page - 1) * limit
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org
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
                 OR JD.JD_OH_ReceivingAgent = @org
              )
        ),
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
                 OR JC.JC_OH_CFSClient = @org
                 OR JC.JC_OH_ShippingLine = @org
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
        ORDER BY COALESCE(JC.JC_SystemLastEditTimeUtc, JC.JC_SystemCreateTimeUtc) DESC
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY;"""
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": jsonable_encoder(obj_list)}

@router.get("/my/cargowise-tracking")
async def func_api_my_cargowise_tracking(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 100), ("page", "int", 0, None, 1)])
    limit = max(1, min(int(oq["limit"] or 100), 300))
    page = max(1, int(oq["page"] or 1))
    offset = (page - 1) * limit
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org
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
                 OR JD.JD_OH_ReceivingAgent = @org
              )
        )
        SELECT
            CONVERT(varchar(36), JS.JS_PK) AS shipment_id,
            JS.JS_UniqueConsignRef AS shipment_reference,
            JS.JS_HouseBill AS house_bill,
            JS.JS_TransportMode AS transport_mode,
            JS.JS_RL_NKOrigin AS origin,
            JS.JS_RL_NKDestination AS destination,
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
        ORDER BY AL.SL_EventTime DESC, AL.SL_PostedTimeUtc DESC
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY;"""
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": jsonable_encoder(obj_list)}

@router.get("/my/cargowise-exceptions")
async def func_api_my_cargowise_exceptions(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 50), ("page", "int", 0, None, 1)])
    limit = max(1, min(int(oq["limit"] or 50), 200))
    page = max(1, int(oq["page"] or 1))
    offset = (page - 1) * limit
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              AND (
                    BuyerOA.OA_OH = @org
                 OR SupplierOA.OA_OH = @org
                 OR JD.JD_OH_Carrier = @org
                 OR JD.JD_OH_SendingAgent = @org
                 OR JD.JD_OH_ReceivingAgent = @org
              )
        ),
        visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org
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
                 OR JD.JD_OH_ReceivingAgent = @org
              )
        ),
        exception_rows AS (
            SELECT
                'Purchase Order' AS source_type,
                CONVERT(varchar(36), JD.JD_PK) AS source_id,
                JD.JD_OrderNumber AS reference,
                'Order Cancelled' AS exception_type,
                'High' AS severity,
                JD.JD_OrderStatus AS status,
                JD.JD_SystemLastEditTimeUtc AS event_at,
                'Purchase order is marked cancelled.' AS note
            FROM visible_orders AS VO
            JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK
            WHERE JD.JD_IsCancelled = 1
            UNION ALL
            SELECT
                'Purchase Order',
                CONVERT(varchar(36), JD.JD_PK),
                JD.JD_OrderNumber,
                'Delivery Date Overdue',
                'Medium',
                JD.JD_OrderStatus,
                JD.JD_DeliveryRequiredBy,
                'Required delivery date has passed.'
            FROM visible_orders AS VO
            JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK
            WHERE JD.JD_IsCancelled = 0
              AND JD.JD_DeliveryRequiredBy IS NOT NULL
              AND JD.JD_DeliveryRequiredBy < SYSUTCDATETIME()
            UNION ALL
            SELECT
                'Shipment',
                CONVERT(varchar(36), JS.JS_PK),
                JS.JS_UniqueConsignRef,
                'Shipment Cancelled',
                'High',
                JS.JS_ShipmentStatus,
                JS.JS_SystemLastEditTimeUtc,
                'Shipment is marked cancelled.'
            FROM visible_shipments AS VS
            JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
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
            FROM visible_shipments AS VS
            JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
            WHERE JS.JS_IsCancelled = 0
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
            FROM visible_shipments AS VS
            JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
            WHERE JS.JS_ScreeningStatus IS NOT NULL
              AND JS.JS_ScreeningStatus NOT IN ('', 'NOT')
        )
        SELECT *
        FROM exception_rows
        ORDER BY event_at DESC
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY;"""
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": jsonable_encoder(obj_list)}

@router.get("/my/cargowise-documents")
async def func_api_my_cargowise_documents(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 50), ("page", "int", 0, None, 1)])
    limit = max(1, min(int(oq["limit"] or 50), 200))
    page = max(1, int(oq["page"] or 1))
    offset = (page - 1) * limit
    sql = f"""
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              AND (
                    BuyerOA.OA_OH = @org
                 OR SupplierOA.OA_OH = @org
                 OR JD.JD_OH_Carrier = @org
                 OR JD.JD_OH_SendingAgent = @org
                 OR JD.JD_OH_ReceivingAgent = @org
              )
        ),
        visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org
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
                 OR JD.JD_OH_ReceivingAgent = @org
              )
        ),
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
                EQ.EQ_SystemLastEditTimeUtc AS updated_at
            FROM dbo.JobRequiredDocument AS EQ
            LEFT JOIN dbo.OrgHeader AS OwnerOH ON OwnerOH.OH_PK = EQ.EQ_OH_DocumentOwner
            LEFT JOIN dbo.OrgHeader AS IssuedByOH ON IssuedByOH.OH_PK = EQ.EQ_OH_IssuedBy
            LEFT JOIN visible_orders AS VO ON EQ.EQ_ParentTableCode = 'JD' AND VO.JD_PK = EQ.EQ_ParentID
            LEFT JOIN visible_shipments AS VS ON EQ.EQ_ParentTableCode = 'JS' AND VS.JS_PK = EQ.EQ_ParentID
            LEFT JOIN visible_consols AS VC ON EQ.EQ_ParentTableCode = 'JK' AND VC.JN_JK = EQ.EQ_ParentID
            WHERE EQ.EQ_IsValid = 1
              AND (
                    EQ.EQ_OH_DocumentOwner = @org
                 OR EQ.EQ_OH_IssuedBy = @org
                 OR VO.JD_PK IS NOT NULL
                 OR VS.JS_PK IS NOT NULL
                 OR VC.JN_JK IS NOT NULL
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
                JDD.JDD_SystemLastEditTimeUtc
            FROM dbo.JobDocumentData AS JDD
            LEFT JOIN visible_shipments AS VS ON JDD.JDD_ParentTableCode = 'JS' AND VS.JS_PK = JDD.JDD_ParentID
            LEFT JOIN visible_consols AS VC ON JDD.JDD_ParentTableCode = 'JK' AND VC.JN_JK = JDD.JDD_ParentID
            WHERE VS.JS_PK IS NOT NULL
               OR VC.JN_JK IS NOT NULL
        )
        SELECT *
        FROM document_rows
        ORDER BY updated_at DESC
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY;"""
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, org_pk)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": jsonable_encoder(obj_list)}

@router.get("/my/cargowise-analytics")
async def func_api_my_cargowise_analytics(*, request: Request):
    app_state = request.app.state
    org_pk = str(request.state.user.get("username") or "").strip()
    if not org_pk: raise Exception("CargoWise org id missing")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    kpis_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              AND (BuyerOA.OA_OH = @org OR SupplierOA.OA_OH = @org OR JD.JD_OH_Carrier = @org OR JD.JD_OH_SendingAgent = @org OR JD.JD_OH_ReceivingAgent = @org)
        ),
        visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org OR JS.JS_OH_DeliveryAgent = @org OR JS.JS_OH_ExportBroker = @org
                 OR JS.JS_OH_HandledOnBehalfOfForwarder = @org OR JS.JS_OH_ImportBroker = @org OR JS.JS_OH_TranshipAgent = @org
                 OR E2OA.OA_OH = @org OR BuyerOA.OA_OH = @org OR SupplierOA.OA_OH = @org
                 OR JD.JD_OH_Carrier = @org OR JD.JD_OH_SendingAgent = @org OR JD.JD_OH_ReceivingAgent = @org
              )
        ),
        visible_containers AS (
            SELECT DISTINCT JC.JC_PK
            FROM dbo.JobContainer AS JC
            LEFT JOIN dbo.JobConShipLink AS JN ON JN.JN_JK = JC.JC_JK
            LEFT JOIN visible_shipments AS VS1 ON VS1.JS_PK = JC.JC_JS_FCLBookingOnlyLink
            LEFT JOIN visible_shipments AS VS2 ON VS2.JS_PK = JN.JN_JS
            WHERE JC.JC_IsValid = 1
              AND (VS1.JS_PK IS NOT NULL OR VS2.JS_PK IS NOT NULL OR JC.JC_OH_CFSClient = @org OR JC.JC_OH_ShippingLine = @org)
        )
        SELECT
            (SELECT COUNT(1) FROM visible_orders) AS purchase_orders,
            (SELECT COUNT(1) FROM visible_shipments) AS shipments,
            (SELECT COUNT(1) FROM visible_containers) AS containers,
            (SELECT COUNT(1) FROM visible_orders AS VO JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK WHERE JD.JD_IsCancelled = 1) AS cancelled_purchase_orders,
            (SELECT COUNT(1) FROM visible_shipments AS VS JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK WHERE JS.JS_IsCancelled = 1) AS cancelled_shipments;"""
    purchase_orders_by_status_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_orders AS (
            SELECT DISTINCT JD.JD_PK
            FROM dbo.JobOrderHeader AS JD
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JD.JD_IsValid = 1
              AND (BuyerOA.OA_OH = @org OR SupplierOA.OA_OH = @org OR JD.JD_OH_Carrier = @org OR JD.JD_OH_SendingAgent = @org OR JD.JD_OH_ReceivingAgent = @org)
        )
        SELECT JD.JD_OrderStatus AS status, COUNT(1) AS count
        FROM visible_orders AS VO
        JOIN dbo.JobOrderHeader AS JD ON JD.JD_PK = VO.JD_PK
        GROUP BY JD.JD_OrderStatus
        ORDER BY COUNT(1) DESC;"""
    shipments_by_status_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org OR JS.JS_OH_DeliveryAgent = @org OR JS.JS_OH_ExportBroker = @org
                 OR JS.JS_OH_HandledOnBehalfOfForwarder = @org OR JS.JS_OH_ImportBroker = @org OR JS.JS_OH_TranshipAgent = @org
                 OR E2OA.OA_OH = @org OR BuyerOA.OA_OH = @org OR SupplierOA.OA_OH = @org
                 OR JD.JD_OH_Carrier = @org OR JD.JD_OH_SendingAgent = @org OR JD.JD_OH_ReceivingAgent = @org
              )
        )
        SELECT JS.JS_ShipmentStatus AS status, COUNT(1) AS count
        FROM visible_shipments AS VS
        JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
        GROUP BY JS.JS_ShipmentStatus
        ORDER BY COUNT(1) DESC;"""
    shipments_by_month_sql = """
        SET NOCOUNT ON;
        DECLARE @org uniqueidentifier = TRY_CONVERT(uniqueidentifier, ?);
        WITH visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org OR JS.JS_OH_DeliveryAgent = @org OR JS.JS_OH_ExportBroker = @org
                 OR JS.JS_OH_HandledOnBehalfOfForwarder = @org OR JS.JS_OH_ImportBroker = @org OR JS.JS_OH_TranshipAgent = @org
                 OR E2OA.OA_OH = @org OR BuyerOA.OA_OH = @org OR SupplierOA.OA_OH = @org
                 OR JD.JD_OH_Carrier = @org OR JD.JD_OH_SendingAgent = @org OR JD.JD_OH_ReceivingAgent = @org
              )
        )
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
        WITH visible_shipments AS (
            SELECT DISTINCT JS.JS_PK
            FROM dbo.JobShipment AS JS
            LEFT JOIN dbo.JobDocAddress AS E2 ON E2.E2_ParentTableCode = 'JS' AND E2.E2_ParentID = JS.JS_PK AND E2.E2_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS E2OA ON E2OA.OA_PK = E2.E2_OA_Address
            LEFT JOIN dbo.JobOrderHeader AS JD ON JD.JD_JS = JS.JS_PK AND JD.JD_IsValid = 1
            LEFT JOIN dbo.OrgAddress AS BuyerOA ON BuyerOA.OA_PK = JD.JD_OA_BuyerAddress
            LEFT JOIN dbo.OrgAddress AS SupplierOA ON SupplierOA.OA_PK = JD.JD_OA_SupplierAddress
            WHERE JS.JS_IsValid = 1
              AND (
                    JS.JS_OH_Creditor = @org OR JS.JS_OH_DeliveryAgent = @org OR JS.JS_OH_ExportBroker = @org
                 OR JS.JS_OH_HandledOnBehalfOfForwarder = @org OR JS.JS_OH_ImportBroker = @org OR JS.JS_OH_TranshipAgent = @org
                 OR E2OA.OA_OH = @org OR BuyerOA.OA_OH = @org OR SupplierOA.OA_OH = @org
                 OR JD.JD_OH_Carrier = @org OR JD.JD_OH_SendingAgent = @org OR JD.JD_OH_ReceivingAgent = @org
              )
        )
        SELECT JS.JS_TransportMode AS transport_mode, COUNT(1) AS count
        FROM visible_shipments AS VS
        JOIN dbo.JobShipment AS JS ON JS.JS_PK = VS.JS_PK
        GROUP BY JS.JS_TransportMode
        ORDER BY COUNT(1) DESC;"""
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(kpis_sql, org_pk)
        kpis_columns = [column[0] for column in cursor.description]
        kpis = [dict(zip(kpis_columns, row)) for row in await cursor.fetchall()]
        await cursor.execute(purchase_orders_by_status_sql, org_pk)
        purchase_orders_by_status_columns = [column[0] for column in cursor.description]
        purchase_orders_by_status = [dict(zip(purchase_orders_by_status_columns, row)) for row in await cursor.fetchall()]
        await cursor.execute(shipments_by_status_sql, org_pk)
        shipments_by_status_columns = [column[0] for column in cursor.description]
        shipments_by_status = [dict(zip(shipments_by_status_columns, row)) for row in await cursor.fetchall()]
        await cursor.execute(shipments_by_month_sql, org_pk)
        shipments_by_month_columns = [column[0] for column in cursor.description]
        shipments_by_month = [dict(zip(shipments_by_month_columns, row)) for row in await cursor.fetchall()]
        await cursor.execute(transport_modes_sql, org_pk)
        transport_modes_columns = [column[0] for column in cursor.description]
        transport_modes = [dict(zip(transport_modes_columns, row)) for row in await cursor.fetchall()]
    analytics_object = {"kpis": kpis[0] if kpis else {}, "purchase_orders_by_status": purchase_orders_by_status, "shipments_by_status": shipments_by_status, "shipments_by_month": shipments_by_month, "transport_modes": transport_modes}
    return {"status": 1, "message": jsonable_encoder(analytics_object)}

@router.get("/admin/cargowise-360")
async def func_api_admin_cargowise_360(*, request: Request):
    app_state = request.app.state
    user = request.state.user or {}
    if int(user.get("role") or 0) != 1: raise Exception("Admin role required")
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 50), ("page", "int", 0, None, 1), ("name", "str", 0, None, "")])
    limit = max(1, min(int(oq["limit"] or 50), 200))
    page = max(1, int(oq["page"] or 1))
    offset = (page - 1) * limit
    name = str(oq.get("name") or "").strip()
    sql = f"""
        SET NOCOUNT ON;
        WITH POs AS (
            SELECT OA.OA_OH AS OrgPK, COUNT(JD.JD_PK) AS TotalPOs
            FROM dbo.JobOrderHeader JD
            INNER JOIN dbo.OrgAddress OA ON JD.JD_OA_BuyerAddress = OA.OA_PK
            GROUP BY OA.OA_OH
        ),
        Shipments AS (
            SELECT
                JSO.JS_E2_OA_OH_Consignee AS OrgPK,
                COUNT(JS.JS_PK) AS TotalShipments,
                SUM(CASE WHEN JS.JS_IsBooking = 1 THEN 1 ELSE 0 END) AS TotalBookings,
                MAX(JS.JS_SystemCreateTimeUtc) AS LastActivityDate
            FROM dbo.JobShipment JS
            INNER JOIN dbo.cvw_JobShipmentOrgs JSO ON JS.JS_PK = JSO.JS_PK
            GROUP BY JSO.JS_E2_OA_OH_Consignee
        ),
        Consols AS (
            SELECT OA.OA_OH AS OrgPK, COUNT(JK.JK_PK) AS TotalConsols
            FROM dbo.JobConsol JK
            INNER JOIN dbo.OrgAddress OA ON JK.JK_OA_SendingForwarderAddress = OA.OA_PK
            GROUP BY OA.OA_OH
        ),
        Finance AS (
            SELECT AH.AH_OH AS OrgPK, COUNT(AH.AH_PK) AS TotalInvoices
            FROM dbo.AccTransactionHeader AH
            GROUP BY AH.AH_OH
        ),
        Combined AS (
            SELECT
                CONVERT(varchar(36), OH.OH_PK) AS org_id,
                OH.OH_FullName AS name,
                ISNULL(POs.TotalPOs, 0) AS total_pos,
                ISNULL(Shipments.TotalBookings, 0) AS total_bookings,
                ISNULL(Shipments.TotalShipments, 0) AS total_shipments,
                ISNULL(Consols.TotalConsols, 0) AS total_consols,
                ISNULL(Finance.TotalInvoices, 0) AS total_invoices,
                Shipments.LastActivityDate AS last_activity_date
            FROM dbo.OrgHeader OH
            LEFT JOIN POs ON OH.OH_PK = POs.OrgPK
            LEFT JOIN Shipments ON OH.OH_PK = Shipments.OrgPK
            LEFT JOIN Consols ON OH.OH_PK = Consols.OrgPK
            LEFT JOIN Finance ON OH.OH_PK = Finance.OrgPK
            WHERE OH.OH_IsActive = 1
              AND OH.OH_IsValid = 1
              AND (? = '' OR LOWER(OH.OH_FullName) LIKE '%' + LOWER(?) + '%')
        )
        SELECT
            org_id,
            name,
            total_pos,
            total_bookings,
            total_shipments,
            total_consols,
            total_invoices,
            last_activity_date
        FROM Combined
        ORDER BY total_shipments DESC, name ASC
        OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY;"""
    async with app_state.client_mssql_read.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(sql, name, name)
        columns = [column[0] for column in cursor.description]
        obj_list = [dict(zip(columns, row)) for row in await cursor.fetchall()]
    return {"status": 1, "message": jsonable_encoder(obj_list)}
