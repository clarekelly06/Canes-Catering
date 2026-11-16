-- Committed 'Canes Catering Company | BTE 423 Team 8
-- reports.sql: the three required reports. Run after schema.sql and seed_data.sql.
USE canes_catering;

-- Report 1. Event menu detail (JOIN across five tables)
-- What menu items were ordered for each event, and what is the line total for each item?
SELECT e.Event_Name,
       e.Event_Date,
       COALESCE(c.Company_Name, CONCAT(c.Client_FName, ' ', c.Client_LName)) AS Client,
       v.Venue_Name,
       m.Item_Name,
       o.Quantity,
       o.Unit_Price,
       o.Quantity * o.Unit_Price AS Line_Total
FROM EVENT_ORDERS o
JOIN EVENT e     ON o.Event_ID = e.Event_ID
JOIN CLIENT c    ON e.Client_ID = c.Client_ID
JOIN VENUE v     ON e.Venue_ID = v.Venue_ID
JOIN MENU_ITEM m ON o.Menu_Item_ID = m.Menu_Item_ID
ORDER BY e.Event_Date, e.Event_ID, m.Item_Name;


-- Report 2. Revenue by category (aggregate + GROUP BY)
-- How much revenue did each menu category generate from completed events?
SELECT m.Item_Category,
       SUM(o.Quantity * o.Unit_Price) AS Total_Revenue
FROM EVENT_ORDERS o
JOIN EVENT e     ON o.Event_ID = e.Event_ID
JOIN MENU_ITEM m ON o.Menu_Item_ID = m.Menu_Item_ID
WHERE e.Status = 'Completed'
GROUP BY m.Item_Category
ORDER BY Total_Revenue DESC;


-- Report 3. Upcoming events (WHERE + ORDER BY with a user filter)
-- Which confirmed events fall within the selected date range and meet the minimum guest count?
SET @start_date = '2026-12-01';
SET @end_date   = '2026-12-31';
SET @min_guests = 100;

SELECT Event_Name, Event_Date, Guest_Count
FROM EVENT
WHERE Event_Date BETWEEN @start_date AND @end_date
  AND Guest_Count >= @min_guests
  AND Status = 'Confirmed'
ORDER BY Event_Date;
