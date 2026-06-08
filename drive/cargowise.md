# CargoWise Database Technical Reference Map

This document outlines the core business flows within the CargoWise database schema, mapped to the exact SQL Server tables and key columns. It is designed as a technical reference for developers writing integrations or reporting queries.

## 1. Organization & Master Data Management
Organizations (clients, vendors, agents, carriers) are heavily normalized. All operational tables (Shipments, Orders) link back to organizations via `OrgAddress` rather than the `OrgHeader` directly.

| Table Name | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `OrgHeader` | The master record for a company. | `OH_PK` (Primary Key), `OH_Code` (Unique text code), `OH_FullName`, `OH_IsConsignee`, `OH_IsActive` |
| `OrgAddress` | The physical addresses and specific roles tied to the Organization. Operational tables link here. | `OA_PK`, `OA_OH` (FK to OrgHeader), `OA_Address1`, `OA_City`, `OA_PostCode`, `OA_RN_NKCountryCode` |
| `OrgCompanyData` | Company-specific data, such as default currencies or terms. | `OC_PK`, `OC_OH` (FK to OrgHeader) |

## 2. Order Management (Purchase Orders)
Used heavily by importers to track procurement before freight is actually booked.

| Table Name | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `JobOrderHeader` | The Purchase Order (PO) header level data. | `JD_PK`, `JD_ParentID`, `JD_OrderNum`, `JD_OA_BuyerAddress` (FK to Buyer Address) |
| `JobOrderLine` | Individual line items on the Purchase Order. | `JL_PK`, `JL_JD` (FK to JobOrderHeader), `JL_ProductCode`, `JL_OrderQty` |

## 3. Forwarding & Execution (Bookings & Shipments)
This is the core module for moving freight. A "Booking" and a "Shipment" live in the exact same table, differentiated only by a boolean flag or status.

| Table Name | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `JobShipment` | Represents both Bookings and Active Shipments (House Bills). | `JS_PK`, `JS_UniqueConsignRef` (Booking #), `JS_IsBooking` (1=Booking, 0=Shipment), `JS_ActualWeight`, `JS_UnitOfWeight`, `JS_ShipmentStatus` |
| `cvw_JobShipmentOrgs` | A highly useful reporting view that flattens out all the related organizations for a shipment. | `JS_PK`, `JS_E2_OA_OH_Consignee`, `JS_E2_OA_OH_Consignor`, `ControllingCustomer_PK` |
| `JobConsol` | The Master Bill / Consolidation. Contains multiple `JobShipment` records (House Bills). | `JC_PK`, `JC_WayBillNum` (Master Bill #), `JC_VesselName`, `JC_VoyageFlight` |
| `JobHeader` | The underlying header that ties Shipments, Consols, and Accounting together. | `JH_PK`, `JH_JobNum`, `JH_ParentID`, `JH_Status` |

## 4. Transport & Cartage
Local pickup and delivery operations (Drayage / Cartage).

| Table Name | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `JobTransport` | Represents a local transport booking (e.g., a truck move). | `TR_PK`, `TR_JobType` (Pickup vs Delivery), `TR_TransportMode`, `TR_EstDeliveryTime` |

## 5. Customs Brokerage
Destination clearance data.

| Table Name | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `JobDeclaration` | The Customs Entry / Declaration. | `JE_PK`, `JE_EntryNum`, `JE_DeclarationType`, `JE_ClearanceStatus` |

## 6. Financials & Accounting
Revenue and cost accruals, along with posted transactions.

| Table Name | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `JobCharge` | The operational charges (Accruals) attached to a Shipment or Consol. | `CR_PK`, `CR_ParentID` (FK to JobHeader), `CR_ChargeCode`, `CR_CostLocal`, `CR_SellLocal` |
| `AccTransaction` | The actual posted accounting transactions (Invoices / Bills). | `AT_PK`, `AT_InvoiceNum`, `AT_TotalAmount`, `AT_PostDate`, `AT_Status` |

## 7. Extensibility (Custom Fields)
CargoWise allows users to create unlimited custom fields. They are stored in a key-value pattern and heavily used in custom integrations (like storing Amazon FBA IDs).

| Table Name | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `GenCustomAddOnValue` | The actual value entered into a custom field for a specific record. | `XV_PK`, `XV_ParentID` (FK to JobShipment/Consol), `XV_Name` (e.g., 'Amazon fbaShipmentId'), `XV_Data` (The string value) |


## 8. Analytics & Tracking Events (Milestones)
CargoWise captures robust tracking events and milestone data. This allows developers to build deep analytics around supply chain performance, exception management, and SLA tracking.

| Table / Concept | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| **Direct Shipment Dates** (`JobShipment`) | The core estimated vs. actual routing dates are stored directly on the shipment row for easy reporting. | `JS_EstDeparture`, `JS_ActDeparture`, `JS_EstArrival`, `JS_ActArrival` |
| **Direct Consol Dates** (`JobConsol`) | Master-level routing dates (e.g., when the vessel actually sails). | `JC_EstDeparture`, `JC_ActDeparture` |
| **Tracking Events** (`WorkflowEvent` / `WorkflowMilestone`) | The granular milestone logs. Every time a container is gated in, boarded, or delayed, an event is logged here. | `EventCode` (e.g., 'DEP' for Departed), `EventDate`, `ParentID` (FK to Shipment/Consol) |


## 9. Container & Equipment Management
CargoWise tracks physical shipping containers and equipment attached to shipments and master consols. This is heavily used by ocean and drayage forwarders.

| Table / Concept | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `JobContainer` | Represents a physical container (e.g., a 40HC or 20GP) attached to a Consol or Shipment. | `CT_PK`, `CT_ContainerNum`, `CT_SealNum`, `CT_ContainerType` |
| `JobContainerMove` | Tracking the individual gate-in / gate-out and terminal movements of the container. | `CM_PK`, `CM_CT` (FK to Container), `CM_MoveType` |


## 10. Warehousing (WMS)
CargoWise contains a full-fledged Warehouse Management System. It handles receiving, putaway, picking, and dispatching inventory.

| Table / Concept | Purpose / Business Concept | Example Key Columns |
| :--- | :--- | :--- |
| `WhsWarehouse` & `WhsLocation` | Defines the physical warehouse and its bin/rack locations. | `WH_Code`, `WL_BinCode` |
| `WhsDocket` | A Warehouse Receipt (Inbound) or Dispatch (Outbound) order. | `DK_PK`, `DK_DocketNum`, `DK_Type` |
| `WhsPick` & `WhsPutaway` | Task tables for warehouse workers moving inventory. | `PK_Status`, `PA_Quantity` |

## SQL

### Total Org Users 

```sql
SELECT TOP (10000) * FROM  dbo.OrgHeader;
```


