# packages
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.get("/management/cargowise-buyer-360")
async def func_api_management_cargowise_buyer_360(*, request: Request):
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
