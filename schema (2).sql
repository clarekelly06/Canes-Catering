-- Committed 'Canes Catering Company | BTE 423 Team 8
-- schema.sql: creates the database and all seven tables.
-- Run order: schema.sql -> seed_data.sql -> reports.sql

CREATE DATABASE IF NOT EXISTS canes_catering;
USE canes_catering;

DROP TABLE IF EXISTS STAFF_ASSIGNMENTS;
DROP TABLE IF EXISTS EVENT_ORDERS;
DROP TABLE IF EXISTS EVENT;
DROP TABLE IF EXISTS MENU_ITEM;
DROP TABLE IF EXISTS STAFF;
DROP TABLE IF EXISTS VENUE;
DROP TABLE IF EXISTS CLIENT;

CREATE TABLE CLIENT (
    Client_ID      INT AUTO_INCREMENT PRIMARY KEY,
    Client_FName   VARCHAR(50)  NOT NULL,
    Client_LName   VARCHAR(50)  NOT NULL,
    Company_Name   VARCHAR(100) NULL,            -- blank for individual clients
    Email_Address  VARCHAR(100) NOT NULL UNIQUE,
    Phone_Number   VARCHAR(20)  NOT NULL,
    Client_Since   DATE         NOT NULL
);

CREATE TABLE VENUE (
    Venue_ID        INT AUTO_INCREMENT PRIMARY KEY,
    Venue_Name      VARCHAR(100) NOT NULL UNIQUE,
    Venue_Street    VARCHAR(100) NOT NULL,
    Venue_City      VARCHAR(50)  NOT NULL,
    Venue_State     CHAR(2)      NOT NULL,
    Venue_Zip_Code  VARCHAR(10)  NOT NULL,
    Venue_Country   VARCHAR(50)  NOT NULL,
    Venue_Capacity  INT          NOT NULL,
    CONSTRAINT chk_venue_capacity CHECK (Venue_Capacity > 0)
);

CREATE TABLE STAFF (
    Staff_ID             INT AUTO_INCREMENT PRIMARY KEY,
    Staff_FName          VARCHAR(50)   NOT NULL,
    Staff_LName          VARCHAR(50)   NOT NULL,
    Staff_Phone_Number   VARCHAR(20)   NOT NULL,
    Staff_Email_Address  VARCHAR(100)  NOT NULL UNIQUE,
    Staff_Role           VARCHAR(20)   NOT NULL,
    Hourly_Rate          DECIMAL(6,2)  NOT NULL,
    CONSTRAINT chk_staff_role CHECK (Staff_Role IN ('Chef', 'Server', 'Bartender', 'Event Lead')),
    CONSTRAINT chk_hourly_rate CHECK (Hourly_Rate > 0)
);

CREATE TABLE MENU_ITEM (
    Menu_Item_ID   INT AUTO_INCREMENT PRIMARY KEY,
    Item_Name      VARCHAR(100) NOT NULL UNIQUE,
    Item_Category  VARCHAR(30)  NOT NULL,
    Current_Price  DECIMAL(8,2) NOT NULL,
    Is_Active      BOOLEAN      NOT NULL DEFAULT TRUE,   -- FALSE = discontinued, kept for order history
    CONSTRAINT chk_item_category CHECK (Item_Category IN ('Appetizer', 'Salad', 'Soup', 'Entree', 'Side',
        'Dessert', 'Non-Alcoholic Beverage', 'Alcoholic Beverage')),
    CONSTRAINT chk_current_price CHECK (Current_Price >= 0)
);

CREATE TABLE EVENT (
    Event_ID     INT AUTO_INCREMENT PRIMARY KEY,
    Client_ID    INT          NOT NULL,
    Venue_ID     INT          NOT NULL,
    Event_Name   VARCHAR(100) NOT NULL,
    Event_Type   VARCHAR(20)  NOT NULL,
    Event_Date   DATE         NOT NULL,
    Guest_Count  INT          NOT NULL,
    Start_Time   TIME         NOT NULL,
    Status       VARCHAR(20)  NOT NULL DEFAULT 'Inquiry',
    CONSTRAINT chk_event_type CHECK (Event_Type IN ('Wedding', 'Corporate', 'Gala', 'Birthday', 'Graduation', 'Other')),
    CONSTRAINT chk_guest_count CHECK (Guest_Count > 0),
    CONSTRAINT chk_event_status CHECK (Status IN ('Inquiry', 'Confirmed', 'Completed', 'Cancelled')),
    CONSTRAINT fk_event_client FOREIGN KEY (Client_ID) REFERENCES CLIENT (Client_ID) ON DELETE RESTRICT,
    CONSTRAINT fk_event_venue  FOREIGN KEY (Venue_ID)  REFERENCES VENUE (Venue_ID)  ON DELETE RESTRICT
    -- Guest_Count <= Venue_Capacity spans two tables, so the Python app enforces it.
);

CREATE TABLE EVENT_ORDERS (
    Event_ID      INT          NOT NULL,
    Menu_Item_ID  INT          NOT NULL,
    Quantity      INT          NOT NULL,
    Unit_Price    DECIMAL(8,2) NOT NULL,   -- price charged at the time of the order
    PRIMARY KEY (Event_ID, Menu_Item_ID),
    CONSTRAINT chk_quantity CHECK (Quantity > 0),
    CONSTRAINT chk_unit_price CHECK (Unit_Price >= 0),
    CONSTRAINT fk_order_event FOREIGN KEY (Event_ID) REFERENCES EVENT (Event_ID) ON DELETE RESTRICT,
    CONSTRAINT fk_order_item  FOREIGN KEY (Menu_Item_ID) REFERENCES MENU_ITEM (Menu_Item_ID) ON DELETE RESTRICT
);

CREATE TABLE STAFF_ASSIGNMENTS (
    Event_ID      INT          NOT NULL,
    Staff_ID      INT          NOT NULL,
    Hours_Worked  DECIMAL(4,1) NULL,       -- blank (NULL) until the event is completed
    Pay_Status    VARCHAR(10)  NOT NULL DEFAULT 'Not Paid',
    PRIMARY KEY (Event_ID, Staff_ID),
    CONSTRAINT chk_hours CHECK (Hours_Worked IS NULL OR Hours_Worked >= 0),
    CONSTRAINT chk_pay_status CHECK (Pay_Status IN ('Not Paid', 'Pending', 'Sent')),
    CONSTRAINT fk_assign_event FOREIGN KEY (Event_ID) REFERENCES EVENT (Event_ID) ON DELETE RESTRICT,
    CONSTRAINT fk_assign_staff FOREIGN KEY (Staff_ID) REFERENCES STAFF (Staff_ID) ON DELETE RESTRICT
);
