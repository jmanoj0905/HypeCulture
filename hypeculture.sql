-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS hypeculture_db;
USE hypeculture_db;

-- ---------------------------------
-- DDL (Data Definition Language)
-- ---------------------------------

-- Users Table: Stores customers, sellers, and admins
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- In a real app, hash passwords!
    user_role ENUM('customer', 'seller', 'admin') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories Table: For shoe types like 'Sneakers', 'Boots', etc.
CREATE TABLE Categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE
);

-- Products Table: Stores general information about each shoe model
CREATE TABLE Products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    brand VARCHAR(50),
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES Categories(category_id)
);

-- Inventory Table: Links sellers to products, defining price and stock
CREATE TABLE Inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT,
    product_id INT,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL,
    FOREIGN KEY (seller_id) REFERENCES Users(user_id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id)
);

-- Addresses Table: To store customer shipping addresses
CREATE TABLE Addresses (
    address_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    address_line1 VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Orders Table: Stores overall order information
CREATE TABLE Orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    address_id INT,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2),
    order_status VARCHAR(20) DEFAULT 'Placed',
    FOREIGN KEY (customer_id) REFERENCES Users(user_id),
    FOREIGN KEY (address_id) REFERENCES Addresses(address_id)
);

-- OrderItems Table: A junction table for items within an order
CREATE TABLE OrderItems (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    inventory_id INT,
    quantity INT NOT NULL,
    price_per_unit DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id),
    FOREIGN KEY (inventory_id) REFERENCES Inventory(inventory_id)
);

-- Cart Table: To hold items before checkout
CREATE TABLE Cart (
    cart_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    inventory_id INT,
    quantity INT NOT NULL,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES Users(user_id),
    FOREIGN KEY (inventory_id) REFERENCES Inventory(inventory_id)
);

-- ---------------------------------
-- DML (Data Manipulation Language) - Sample Data
-- ---------------------------------

-- Users
INSERT INTO Users (first_name, last_name, email, password_hash, user_role) VALUES
('Alice', 'Wonder', 'alice@email.com', 'pass123', 'customer'),
('Bob', 'Builder', 'bob@email.com', 'pass123', 'customer'),
('Charlie', 'Shoes', 'charlie@seller.com', 'pass123', 'seller'),
('Diana', 'Kicks', 'diana@seller.com', 'pass123', 'seller'),
('Edward', 'Admin', 'admin@hypeculture.com', 'adminpass', 'admin');

-- Categories
INSERT INTO Categories (category_name) VALUES ('Sneakers'), ('Boots'), ('Formal Shoes');

-- Products
INSERT INTO Products (product_name, brand, category_id) VALUES
('Air Jordan 4', 'Nike', 1),
('Panda Dunks', 'Nike', 1),
('Yeezy Boost 350', 'Adidas', 1),
('Classic Timberland', 'Timberland', 2);

-- Inventory (Sellers listing products)
INSERT INTO Inventory (seller_id, product_id, price, stock_quantity) VALUES
(3, 1, 250.00, 10), -- Charlie sells Jordan 4s
(4, 1, 245.00, 5),  -- Diana sells Jordan 4s cheaper
(3, 2, 150.00, 20), -- Charlie sells Panda Dunks
(4, 3, 220.00, 15); -- Diana sells Yeezys

-- ---------------------------------
-- Stored Procedures and Functions
-- ---------------------------------

-- Procedure to add an item to a customer's cart
DELIMITER $$
CREATE PROCEDURE AddToCart(
    IN p_customer_id INT,
    IN p_inventory_id INT,
    IN p_quantity INT
)
BEGIN
    DECLARE existing_quantity INT DEFAULT 0;

    -- Check if the item already exists in the cart
    SELECT quantity INTO existing_quantity
    FROM Cart
    WHERE customer_id = p_customer_id AND inventory_id = p_inventory_id;

    IF existing_quantity > 0 THEN
        -- Update quantity if item is already in cart
        UPDATE Cart
        SET quantity = quantity + p_quantity
        WHERE customer_id = p_customer_id AND inventory_id = p_inventory_id;
    ELSE
        -- Insert new item into cart
        INSERT INTO Cart(customer_id, inventory_id, quantity)
        VALUES (p_customer_id, p_inventory_id, p_quantity);
    END IF;
END$$
DELIMITER ;


-- Procedure to place an order from the cart
DELIMITER $$
CREATE PROCEDURE PlaceOrder(
    IN p_customer_id INT, 
    IN p_first_name VARCHAR(50), 
    IN p_last_name VARCHAR(50), 
    IN p_address_line1 VARCHAR(255), 
    IN p_city VARCHAR(100), 
    IN p_state VARCHAR(100), 
    IN p_postal_code VARCHAR(20)
)
BEGIN
    DECLARE v_address_id INT;
    DECLARE v_order_id INT;
    DECLARE v_total_amount DECIMAL(10, 2) DEFAULT 0;
    DECLARE finished INTEGER DEFAULT 0;
    DECLARE v_inventory_id INT;
    DECLARE v_quantity INT;
    DECLARE v_price_per_unit DECIMAL(10, 2);

    -- Cursor to iterate through cart items
    DECLARE cart_cursor CURSOR FOR
        SELECT c.inventory_id, c.quantity, i.price
        FROM Cart c
        JOIN Inventory i ON c.inventory_id = i.inventory_id
        WHERE c.customer_id = p_customer_id;
        
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET finished = 1;

    -- Add or get address
    INSERT INTO Addresses(user_id, address_line1, city, state, postal_code)
    VALUES(p_customer_id, p_address_line1, p_city, p_state, p_postal_code);
    SET v_address_id = LAST_INSERT_ID();
    
    -- Update user's name if it's different (optional)
    UPDATE Users SET first_name = p_first_name, last_name = p_last_name WHERE user_id = p_customer_id;

    -- Calculate total amount
    SELECT SUM(i.price * c.quantity) INTO v_total_amount
    FROM Cart c
    JOIN Inventory i ON c.inventory_id = i.inventory_id
    WHERE c.customer_id = p_customer_id;

    -- Create a new order
    INSERT INTO Orders (customer_id, address_id, total_amount)
    VALUES (p_customer_id, v_address_id, v_total_amount);
    SET v_order_id = LAST_INSERT_ID();

    -- Open the cursor to move cart items to order items
    OPEN cart_cursor;
    
    get_cart_item: LOOP
        FETCH cart_cursor INTO v_inventory_id, v_quantity, v_price_per_unit;
        IF finished = 1 THEN
            LEAVE get_cart_item;
        END IF;

        -- Insert into OrderItems
        INSERT INTO OrderItems (order_id, inventory_id, quantity, price_per_unit)
        VALUES (v_order_id, v_inventory_id, v_quantity, v_price_per_unit);
    END LOOP get_cart_item;
    
    CLOSE cart_cursor;

    -- Clear the customer's cart
    DELETE FROM Cart WHERE customer_id = p_customer_id;

    SELECT v_order_id AS new_order_id;
END$$
DELIMITER ;

-- Function to calculate total items in a user's cart
DELIMITER $$
CREATE FUNCTION GetCartItemCount(p_customer_id INT)
RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE item_count INT;
    SELECT SUM(quantity) INTO item_count FROM Cart WHERE customer_id = p_customer_id;
    RETURN IFNULL(item_count, 0);
END$$
DELIMITER ;

-- ---------------------------------
-- Triggers
-- ---------------------------------

-- Trigger to update inventory stock after an order is placed
DELIMITER $$
CREATE TRIGGER AfterOrderItemInsert
AFTER INSERT ON OrderItems
FOR EACH ROW
BEGIN
    UPDATE Inventory
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE inventory_id = NEW.inventory_id;
END$$
DELIMITER ;