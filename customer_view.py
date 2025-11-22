# customer_view.py — Streamlit version (fixed)
import time
import streamlit as st
import pandas as pd

def _fetchall(cursor, query, params=None):
    cursor.execute(query, params or ())
    return cursor.fetchall()

def _safe_default_index(options_list, stored_value):
    """Return the index of stored_value in options_list if present, else 0."""
    try:
        return options_list.index(int(stored_value))
    except Exception:
        return 0

def show_customer_menu(connection, user_id):
    """Streamlit main menu for the logged-in customer."""
    st.session_state.setdefault("customer_view", "Browse Products")
    st.session_state.setdefault("chosen_category_id", None)
    st.session_state.setdefault("chosen_product_id", None)

    st.subheader("👟 Customer Menu")

    view = st.radio(
        "Go to",
        ["Browse Products", "My Cart", "Checkout", "Order History", "Logout"],
        index=_safe_default_index(
            ["Browse Products", "My Cart", "Checkout", "Order History", "Logout"],
            st.session_state["customer_view"]
        ),
        horizontal=True,
        key="customer_view",
    )

    if view == "Browse Products":
        browse_products(connection, user_id)
    elif view == "My Cart":
        view_cart(connection, user_id)
    elif view == "Checkout":
        checkout(connection, user_id)
    elif view == "Order History":
        view_order_history(connection, user_id)
    elif view == "Logout":
        st.info("Logging out...")
        if st.button("Confirm Log out"):
            st.session_state.user = None
            st.rerun()

def browse_products(connection, user_id):
    """Browse categories → products → sellers, add to cart."""
    c = connection.cursor()

    # Categories
    categories = _fetchall(c, "SELECT category_id, category_name FROM Categories")
    if not categories:
        st.warning("No categories found.")
        c.close()
        return

    cat_df = pd.DataFrame(categories, columns=["category_id", "category_name"])
    # Python-native options and lookup
    cat_options = [int(x) for x in cat_df["category_id"].tolist()]
    cat_name_by_id = {int(row["category_id"]): row["category_name"] for _, row in cat_df.iterrows()}

    st.markdown("#### Select a Category")
    cat_choice = st.selectbox(
        "Category",
        options=cat_options,
        format_func=lambda cid: cat_name_by_id.get(int(cid), str(cid)),
        index=_safe_default_index(cat_options, st.session_state.get("chosen_category_id")),
    )
    st.session_state["chosen_category_id"] = int(cat_choice)

    # Products in selected category
    products = _fetchall(
        c,
        "SELECT product_id, product_name FROM Products WHERE category_id = %s",
        (st.session_state["chosen_category_id"],),
    )
    c.close()

    if not products:
        st.info("No products in this category yet.")
        return

    prod_df = pd.DataFrame(products, columns=["product_id", "product_name"])
    prod_options = [int(x) for x in prod_df["product_id"].tolist()]
    prod_name_by_id = {int(row["product_id"]): row["product_name"] for _, row in prod_df.iterrows()}

    st.markdown("#### Select a Product")
    prod_choice = st.selectbox(
        "Product",
        options=prod_options,
        format_func=lambda pid: prod_name_by_id.get(int(pid), str(pid)),
        index=_safe_default_index(prod_options, st.session_state.get("chosen_product_id")),
    )
    st.session_state["chosen_product_id"] = int(prod_choice)

    # Sellers for product (cheapest first)
    c = connection.cursor()
    sellers = _fetchall(
        c,
        """
        SELECT sp.inventory_id, u.first_name, u.last_name, sp.price, sp.stock_quantity
        FROM Inventory sp
        JOIN Users u ON sp.seller_id = u.user_id
        WHERE sp.product_id = %s AND sp.stock_quantity > 0
        ORDER BY sp.price ASC
        """,
        (st.session_state["chosen_product_id"],),
    )
    c.close()

    if not sellers:
        st.warning("Sorry, this product is currently out of stock or not sold.")
        return

    sellers_df = pd.DataFrame(
        sellers, columns=["inventory_id", "seller_first", "seller_last", "price", "stock"]
    )

    best = sellers_df.iloc[0]
    st.success(
        f"**Best price**: ${best['price']:.2f} from {best['seller_first']} {best['seller_last']} "
        f"(Stock: {int(best['stock'])})"
    )

    with st.expander("See all sellers", expanded=False):
        st.dataframe(
            sellers_df.rename(
                columns={
                    "inventory_id": "Inventory ID",
                    "seller_first": "Seller First",
                    "seller_last": "Seller Last",
                    "price": "Price",
                    "stock": "Stock",
                }
            ),
            use_container_width=True,
        )

    st.markdown("#### Add to Cart")
    add_mode = st.radio("Choose seller", ["Best Price", "Pick from list"], horizontal=True)
    if add_mode == "Best Price":
        inventory_id = int(best["inventory_id"])
    else:
        # Use a clean Python list of row indices
        seller_row_indices = [int(i) for i in range(len(sellers_df))]
        seller_choice = st.selectbox(
            "Seller",
            options=seller_row_indices,
            format_func=lambda idx: (
                f"{sellers_df.loc[idx, 'seller_first']} {sellers_df.loc[idx, 'seller_last']} — "
                f"${sellers_df.loc[idx, 'price']:.2f} (Stock: {int(sellers_df.loc[idx, 'stock'])})"
            ),
        )
        inventory_id = int(sellers_df.loc[seller_choice, "inventory_id"])

    qty = st.number_input("Quantity", min_value=1, step=1, value=1)

    if st.button("Add to Cart"):
        _add_to_cart(connection, user_id, inventory_id, qty)

def _add_to_cart(connection, user_id, inventory_id, quantity):
    """Adds/updates item in Cart table."""
    try:
        c = connection.cursor()
        # Validate stock
        c.execute("SELECT stock_quantity FROM Inventory WHERE inventory_id = %s", (inventory_id,))
        row = c.fetchone()
        if not row:
            st.error("Selected inventory item not found.")
            c.close()
            return

        stock = int(row[0])
        if quantity <= 0:
            st.warning("Quantity must be positive.")
            c.close()
            return
        if quantity > stock:
            st.warning(f"Only {stock} left in stock.")
            c.close()
            return

        # Upsert-like behavior
        c.execute(
            "SELECT cart_id, quantity FROM Cart WHERE customer_id = %s AND inventory_id = %s",
            (user_id, inventory_id),
        )
        existing = c.fetchone()
        if existing:
            cart_id, current_qty = existing
            new_qty = int(current_qty) + int(quantity)
            if new_qty > stock:
                st.warning(
                    f"Adding {quantity} would exceed stock ({stock}). "
                    f"You currently have {current_qty} in cart."
                )
                c.close()
                return
            c.execute("UPDATE Cart SET quantity = %s WHERE cart_id = %s", (new_qty, cart_id))
        else:
            c.execute(
                "INSERT INTO Cart (customer_id, inventory_id, quantity) VALUES (%s, %s, %s)",
                (user_id, inventory_id, int(quantity)),
            )
        connection.commit()
        st.success("Item added to cart successfully!")
    except Exception as e:
        connection.rollback()
        st.error(f"An error occurred: {e}")
    finally:
        try:
            c.close()
        except Exception:
            pass

def view_cart(connection, user_id):
    """Displays the contents of the user's cart."""
    c = connection.cursor()
    query = """
    SELECT
        p.product_name,
        u.first_name AS seller_name,
        i.price,
        c.quantity,
        (i.price * c.quantity) AS subtotal,
        c.cart_id
    FROM
        Cart AS c
    JOIN
        Inventory AS i ON c.inventory_id = i.inventory_id
    JOIN
        Products AS p ON i.product_id = p.product_id
    JOIN
        Users AS u ON i.seller_id = u.user_id
    WHERE
        c.customer_id = %s;
    """
    try:
        c.execute(query, (user_id,))
        rows = c.fetchall()

        st.markdown("#### 🛒 Your Shopping Cart")
        if not rows:
            st.info("Your cart is empty.")
            return

        df = pd.DataFrame(
            rows, columns=["Product", "Seller", "Price", "Qty", "Subtotal", "cart_id"]
        )
        total = float(df["Subtotal"].sum())

        st.dataframe(df[["Product", "Seller", "Price", "Qty", "Subtotal"]], use_container_width=True)
        st.markdown(f"**TOTAL:** ${total:.2f}")

        with st.expander("Update quantities / remove items"):
            for _, r in df.iterrows():
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.write(f"{r['Product']} (by {r['Seller']})")
                with col2:
                    new_qty = st.number_input(
                        f"Qty for cart #{int(r['cart_id'])}",
                        min_value=0,
                        step=1,
                        value=int(r["Qty"]),
                        key=f"qty_{int(r['cart_id'])}",
                    )
                with col3:
                    if st.button("Update", key=f"upd_{int(r['cart_id'])}"):
                        _update_cart_item(connection, int(r["cart_id"]), int(new_qty))
                        st.rerun()

    except Exception as e:
        st.error(f"An error occurred while viewing cart: {e}")
    finally:
        c.close()

def _update_cart_item(connection, cart_id, new_qty):
    try:
        c = connection.cursor()
        if int(new_qty) == 0:
            c.execute("DELETE FROM Cart WHERE cart_id = %s", (cart_id,))
        else:
            c.execute("UPDATE Cart SET quantity = %s WHERE cart_id = %s", (int(new_qty), cart_id))
        connection.commit()
        st.success("Cart updated.")
    except Exception as e:
        connection.rollback()
        st.error(f"Could not update cart: {e}")
    finally:
        try:
            c.close()
        except Exception:
            pass

def checkout(connection, user_id):
    """Checkout flow using a single transaction."""
    c = connection.cursor()
    c.execute(
        """
        SELECT c.inventory_id, c.quantity, i.price, i.stock_quantity
        FROM Cart c JOIN Inventory i ON c.inventory_id = i.inventory_id
        WHERE c.customer_id = %s;
        """,
        (user_id,),
    )
    cart_items = c.fetchall()
    c.close()

    st.markdown("#### 💳 Checkout")
    if not cart_items:
        st.info("Your cart is empty. Add items before checking out.")
        return

    total_amount = 0.0
    for inv_id, qty, price, stock in cart_items:
        if int(qty) > int(stock):
            st.error(f"Not enough stock for item ID {inv_id}. Only {stock} left.")
            return
        total_amount += int(qty) * float(price)

    st.write(f"**Order Total:** ${total_amount:.2f}")

    with st.form("shipping_form"):
        st.markdown("##### Shipping Details")
        address_line = st.text_input("Address Line 1")
        city = st.text_input("City")
        state = st.text_input("State")
        postal_code = st.text_input("Postal Code")
        submitted = st.form_submit_button("Pay Now")

    if submitted:
        if not all([address_line, city, state, postal_code]):
            st.warning("All fields are required.")
            return

        cur = connection.cursor(buffered=True)
        try:
            cur.execute(
                "INSERT INTO Addresses (user_id, address_line1, city, state, postal_code) VALUES (%s, %s, %s, %s, %s)",
                (user_id, address_line, city, state, postal_code),
            )
            address_id = cur.lastrowid

            cur.execute(
                "INSERT INTO Orders (customer_id, address_id, total_amount) VALUES (%s, %s, %s)",
                (user_id, address_id, total_amount),
            )
            order_id = cur.lastrowid

            for inv_id, qty, price, stock in cart_items:
                cur.execute(
                    "INSERT INTO OrderItems (order_id, inventory_id, quantity, price_per_unit) VALUES (%s, %s, %s, %s)",
                    (order_id, inv_id, int(qty), float(price)),
                )
                new_stock = int(stock) - int(qty)
                cur.execute(
                    "UPDATE Inventory SET stock_quantity = %s WHERE inventory_id = %s",
                    (new_stock, inv_id),
                )

            cur.execute("DELETE FROM Cart WHERE customer_id = %s", (user_id,))
            connection.commit()

            with st.spinner("Processing payment..."):
                time.sleep(1)
            st.success(f"Payment successful! Your order #{order_id} has been placed.")
        except Exception as e:
            connection.rollback()
            st.error(f"An error occurred during checkout: {e}. Transaction rolled back.")
        finally:
            cur.close()

def view_order_history(connection, user_id):
    """Displays past orders and their items."""
    c = connection.cursor()
    try:
        c.execute(
            """
            SELECT o.order_id, o.order_date, o.total_amount, a.address_line1, a.city
            FROM Orders o JOIN Addresses a ON o.address_id = a.address_id
            WHERE o.customer_id = %s
            ORDER BY o.order_date DESC;
            """,
            (user_id,),
        )
        orders = c.fetchall()

        st.markdown("#### 📜 Your Order History")
        if not orders:
            st.info("You have no past orders.")
            return

        for (order_id, order_date, total, address, city) in orders:
            with st.expander(
                f"Order #{order_id} — {order_date.strftime('%Y-%m-%d')} — Total: ${float(total):.2f}",
                expanded=False,
            ):
                st.caption(f"Shipped to: {address}, {city}")

                item_c = connection.cursor()
                item_c.execute(
                    """
                    SELECT p.product_name, u.first_name AS seller_name, oi.quantity, oi.price_per_unit
                    FROM OrderItems oi
                    JOIN Inventory i ON oi.inventory_id = i.inventory_id
                    JOIN Products p ON i.product_id = p.product_id
                    JOIN Users u ON i.seller_id = u.user_id
                    WHERE oi.order_id = %s;
                    """,
                    (order_id,),
                )
                items = item_c.fetchall()
                item_c.close()

                if items:
                    df = pd.DataFrame(items, columns=["Product", "Seller", "Qty", "Price per unit"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.write("_No items found for this order._")
    except Exception as e:
        st.error(f"An error occurred while fetching order history: {e}")
    finally:
        c.close()
