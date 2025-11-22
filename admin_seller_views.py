# admin_seller_views.py — Streamlit version
import streamlit as st
import pandas as pd

# ---------- small helpers ----------
def _fetchall(cursor, query, params=None):
    cursor.execute(query, params or ())
    return cursor.fetchall()

def _fetchone(cursor, query, params=None):
    cursor.execute(query, params or ())
    return cursor.fetchone()

# ---------- Admin helpers ----------
def add_new_product(connection):
    """Streamlit UI for admin to add a new product to Products."""
    c = connection.cursor()
    try:
        st.markdown("### ➕ Add New Product to Catalog")

        # categories list
        cats = _fetchall(c, "SELECT category_id, category_name FROM Categories")
        if not cats:
            st.warning("No categories found. Add categories first.")
            return
        cat_df = pd.DataFrame(cats, columns=["category_id", "category_name"])

        with st.form("add_product_form"):
            product_name = st.text_input("Product name (e.g., New Balance 550)")
            brand = st.text_input("Brand")
            category_id = st.selectbox(
                "Category",
                options=cat_df["category_id"],
                format_func=lambda cid: f"{cid} — {cat_df.loc[cat_df['category_id']==cid, 'category_name'].values[0]}",
            )
            submitted = st.form_submit_button("Add Product")

        if submitted:
            if not product_name or not brand or category_id is None:
                st.warning("All fields are required.")
                return
            try:
                _fetchone(c, "SELECT 1 FROM Categories WHERE category_id=%s", (int(category_id),))
                c.execute(
                    "INSERT INTO Products (product_name, brand, category_id) VALUES (%s, %s, %s)",
                    (product_name, brand, int(category_id))
                )
                connection.commit()
                st.success(f"Product '{product_name}' added successfully.")
            except Exception as e:
                connection.rollback()
                st.error(f"❌ Error adding product: {e}")
    finally:
        c.close()


def add_new_user(connection):
    """Streamlit UI for admin to add a new user."""
    c = connection.cursor()
    try:
        st.markdown("### 👤 Add New User")
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First name")
            with col2:
                last_name = st.text_input("Last name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["customer", "seller"])
            submitted = st.form_submit_button("Create User")

        if submitted:
            if not all([first_name, last_name, email, password, role]):
                st.warning("All fields are required.")
                return
            try:
                c.execute(
                    "INSERT INTO Users (first_name, last_name, email, password_hash, user_role) VALUES (%s, %s, %s, %s, %s)",
                    (first_name, last_name, email, password, role)
                )
                connection.commit()
                st.success(f"User '{email}' created successfully as a '{role}'.")
            except Exception as e:
                connection.rollback()
                st.error(f"❌ Error adding user: {e}")
    finally:
        c.close()


def remove_user(connection):
    """Streamlit UI for admin to remove a user."""
    c = connection.cursor()
    try:
        st.markdown("### 🗑️ Remove User")
        with st.form("remove_user_form"):
            user_id_str = st.text_input("User ID to remove")
            submitted = st.form_submit_button("Remove")

        if submitted:
            if not user_id_str.strip().isdigit():
                st.warning("Please enter a valid numeric User ID.")
                return
            user_id = int(user_id_str)
            try:
                c.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
                if c.rowcount > 0:
                    connection.commit()
                    st.success(f"User with ID {user_id} has been removed.")
                else:
                    st.info("User ID not found.")
            except Exception as e:
                connection.rollback()
                st.error("❌ Error removing user: "
                         f"{e}\n(Note: You cannot remove a user who has existing orders or inventory listings.)")
    finally:
        c.close()


# ---------- Admin main ----------
def show_admin_menu(connection):
    """Streamlit admin menu."""
    st.subheader("👑 Admin Menu")

    tabs = st.tabs([
        "All Users",
        "All Products",
        "All Orders",
        "Add Product",
        "Add User",
        "Remove User",
        "Logout",
    ])

    # 1. All Users
    with tabs[0]:
        c = connection.cursor()
        try:
            rows = _fetchall(c, "SELECT user_id, first_name, last_name, email, user_role FROM Users")
            if rows:
                df = pd.DataFrame(rows, columns=["User ID", "First", "Last", "Email", "Role"])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No users found.")
        except Exception as e:
            st.error(f"Error loading users: {e}")
        finally:
            c.close()

    # 2. All Products
    with tabs[1]:
        c = connection.cursor()
        try:
            rows = _fetchall(c, "SELECT product_id, product_name, brand, category_id FROM Products")
            if rows:
                df = pd.DataFrame(rows, columns=["Product ID", "Product", "Brand", "Category ID"])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No products found.")
        except Exception as e:
            st.error(f"Error loading products: {e}")
        finally:
            c.close()

    # 3. All Orders
    with tabs[2]:
        c = connection.cursor()
        try:
            rows = _fetchall(c, "SELECT order_id, customer_id, total_amount, order_status, order_date FROM Orders")
            if rows:
                df = pd.DataFrame(rows, columns=["Order ID", "Customer ID", "Total", "Status", "Date"])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No orders found.")
        except Exception as e:
            st.error(f"Error loading orders: {e}")
        finally:
            c.close()

    # 4. Add Product
    with tabs[3]:
        add_new_product(connection)

    # 5. Add User
    with tabs[4]:
        add_new_user(connection)

    # 6. Remove User
    with tabs[5]:
        remove_user(connection)

    # 7. Logout
    with tabs[6]:
        st.info("Logging out ends your admin session.")
        if st.button("Confirm Log out"):
            st.session_state.user = None
            st.rerun()


# ---------- Seller main ----------
def show_seller_menu(connection, user_id):
    """Streamlit seller menu (listings CRUD)."""
    st.subheader("💼 Seller Menu")

    tabs = st.tabs([
        "My Listings",
        "Add Listing",
        "Update Listing",
        "Remove Listing",
        "Logout",
    ])

    # 1) View My Listings
    with tabs[0]:
        c = connection.cursor()
        try:
            rows = _fetchall(c, """
                SELECT i.inventory_id, p.product_name, i.price, i.stock_quantity
                FROM Inventory AS i
                JOIN Products AS p ON i.product_id = p.product_id
                WHERE i.seller_id = %s
                ORDER BY i.inventory_id DESC
            """, (user_id,))
            if rows:
                df = pd.DataFrame(rows, columns=["Inventory ID", "Product", "Price", "Stock"])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("You have no listings yet.")
        except Exception as e:
            st.error(f"An error occurred: {e}")
        finally:
            c.close()

    # 2) Add New Listing
    with tabs[1]:
        c = connection.cursor()
        try:
            st.markdown("### ➕ Add New Listing")

            # Pick from master products
            prows = _fetchall(c, "SELECT product_id, product_name, brand FROM Products ORDER BY product_name ASC")
            if not prows:
                st.info("No products in the master catalog. Ask admin to add products first.")
            else:
                pdf = pd.DataFrame(prows, columns=["product_id", "product_name", "brand"])
                with st.form("add_listing_form"):
                    product_id = st.selectbox(
                        "Master Product",
                        options=pdf["product_id"],
                        format_func=lambda pid: f"{int(pid)} — {pdf.loc[pdf['product_id']==pid, 'product_name'].values[0]} ({pdf.loc[pdf['product_id']==pid, 'brand'].values[0]})"
                    )
                    price = st.number_input("Price", min_value=0.0, step=0.01)
                    stock = st.number_input("Stock quantity", min_value=0, step=1)
                    submitted = st.form_submit_button("Create Listing")

                if submitted:
                    try:
                        c.execute(
                            "INSERT INTO Inventory (seller_id, product_id, price, stock_quantity) VALUES (%s, %s, %s, %s)",
                            (user_id, int(product_id), float(price), int(stock))
                        )
                        connection.commit()
                        st.success("✅ Listing added successfully!")
                    except Exception as e:
                        connection.rollback()
                        st.error(f"Error adding listing: {e}")
        finally:
            c.close()

    # 3) Update a Listing
    with tabs[2]:
        c = connection.cursor()
        try:
            st.markdown("### ✏️ Update Listing (Stock/Price)")
            # load seller listings
            rows = _fetchall(c, """
                SELECT i.inventory_id, p.product_name, i.price, i.stock_quantity
                FROM Inventory AS i
                JOIN Products AS p ON i.product_id = p.product_id
                WHERE i.seller_id = %s
                ORDER BY i.inventory_id DESC
            """, (user_id,))
            if not rows:
                st.info("No listings to update.")
            else:
                df = pd.DataFrame(rows, columns=["inventory_id", "Product", "Price", "Stock"])
                choice = st.selectbox(
                    "Choose a listing",
                    options=df["inventory_id"],
                    format_func=lambda inv: f"#{int(inv)} — {df.loc[df['inventory_id']==inv, 'Product'].values[0]}"
                )
                current_row = df.loc[df["inventory_id"] == choice].iloc[0]
                col1, col2 = st.columns(2)
                with col1:
                    new_price = st.number_input("New price (leave same to keep)", min_value=0.0, step=0.01, value=float(current_row["Price"]))
                with col2:
                    new_stock = st.number_input("New stock (leave same to keep)", min_value=0, step=1, value=int(current_row["Stock"]))

                if st.button("Update Listing"):
                    try:
                        # Only update if changed
                        if float(new_price) != float(current_row["Price"]):
                            c.execute(
                                "UPDATE Inventory SET price = %s WHERE inventory_id = %s AND seller_id = %s",
                                (float(new_price), int(choice), user_id)
                            )
                        if int(new_stock) != int(current_row["Stock"]):
                            c.execute(
                                "UPDATE Inventory SET stock_quantity = %s WHERE inventory_id = %s AND seller_id = %s",
                                (int(new_stock), int(choice), user_id)
                            )
                        connection.commit()
                        st.success("✅ Listing updated!")
                        st.experimental_rerun()
                    except Exception as e:
                        connection.rollback()
                        st.error(f"Error updating listing: {e}")
        finally:
            c.close()

    # 4) Remove a Listing
    with tabs[3]:
        c = connection.cursor()
        try:
            st.markdown("### 🗑️ Remove Listing")
            rows = _fetchall(c, """
                SELECT i.inventory_id, p.product_name, i.price, i.stock_quantity
                FROM Inventory AS i
                JOIN Products AS p ON i.product_id = p.product_id
                WHERE i.seller_id = %s
                ORDER BY i.inventory_id DESC
            """, (user_id,))
            if not rows:
                st.info("No listings to remove.")
            else:
                df = pd.DataFrame(rows, columns=["inventory_id", "Product", "Price", "Stock"])
                listing_id = st.selectbox(
                    "Listing to remove",
                    options=df["inventory_id"],
                    format_func=lambda inv: f"#{int(inv)} — {df.loc[df['inventory_id']==inv, 'Product'].values[0]} (${df.loc[df['inventory_id']==inv, 'Price'].values[0]:.2f}, stock {int(df.loc[df['inventory_id']==inv, 'Stock'])})"
                )
                if st.button("Remove Listing"):
                    try:
                        c.execute("DELETE FROM Inventory WHERE inventory_id = %s AND seller_id = %s", (int(listing_id), user_id))
                        if c.rowcount > 0:
                            connection.commit()
                            st.success(f"✅ Listing #{int(listing_id)} has been removed.")
                            st.experimental_rerun()
                        else:
                            st.info("Listing ID not found or you do not have permission to remove it.")
                    except Exception as e:
                        connection.rollback()
                        st.error(f"Error removing listing: {e}")
        finally:
            c.close()

    # 5) Logout
    with tabs[4]:
        st.info("Logging out ends your seller session.")
        if st.button("Confirm Log out"):
            st.session_state.user = None
            st.rerun()
