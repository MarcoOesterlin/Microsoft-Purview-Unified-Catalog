import pandas as pd
import streamlit as st
import get_data
import add_tag
import delete_tag
import get_entra_id_users
import add_owner
import time
import asyncio

def load_data():
    df = get_data.main()  # Using the imported main function directly
    
    # Handle None or empty DataFrame
    if df is None or df.empty:
        print("Warning: No data returned from purview_dg_curator_portal.main()")
        # Create empty DataFrame with expected columns
        df = pd.DataFrame(columns=['id', 'name', 'assetType', 'entityType', 'contact', 'tag', 'classification', 'description'])
        return df
    
    # Print available columns and first few rows for debugging
    print("Available columns:", df.columns.tolist())
    print("\nFirst few rows of data:")
    print(df.head())
    print(f"\nTotal number of rows: {len(df)}")
    
    # Map the expected columns to actual column names
    column_mapping = {
        'id': 'id',
        'name': 'name',
        'assetType': 'assetType',
        'entityType': 'entityType',
        'contact': 'contact',
        'tag': 'tag',  # Try the most likely column name for tags
        'classification': 'classification',  # Try the most likely column name for classification
        'description': 'description'  # Add description field
    }
    
    # Ensure all expected columns exist
    for col in ['id', 'name', 'assetType', 'entityType', 'contact', 'tag', 'classification', 'description']:
        if column_mapping[col] not in df.columns:
            print(f"Warning: Column {column_mapping[col]} not found in DataFrame")
            # Add empty column with expected name
            df[column_mapping[col]] = None
    
    # Select all columns (including empty ones)
    selected_columns = [column_mapping[col] for col in ['id', 'name', 'assetType', 'entityType', 'contact', 'tag', 'classification', 'description']]
    df = df[selected_columns]
    
    # Rename columns back to expected names
    reverse_mapping = {v: k for k, v in column_mapping.items()}
    df = df.rename(columns=reverse_mapping)
    
    # Print final DataFrame structure
    print("\nFinal DataFrame columns:", df.columns.tolist())
    print("\nFinal DataFrame first few rows:")
    print(df.head())
    
    return df

def refresh_page():
    time.sleep(1)  # Add a small delay
    st.rerun()

# Initialize success message state
if 'success_message' not in st.session_state:
    st.session_state.success_message = None

# Initialize tab4 reset state
if 'tab4_reset' not in st.session_state:
    st.session_state.tab4_reset = False

# Initialize selected IDs state
if 'selected_ids' not in st.session_state:
    st.session_state.selected_ids = []

# Initialize selected owners state
if 'selected_owners' not in st.session_state:
    st.session_state.selected_owners = []

# Initialize selected owner IDs state
if 'selected_owner_ids' not in st.session_state:
    st.session_state.selected_owner_ids = []

# Initialize current selected owners state
if 'current_selected_owners' not in st.session_state:
    st.session_state.current_selected_owners = []

# Initialize comments state
if 'owner_comments' not in st.session_state:
    st.session_state.owner_comments = ""

# Initialize role state
if 'owner_role' not in st.session_state:
    st.session_state.owner_role = "Owner"

# Initialize editor key for forcing rerun
if 'editor_key' not in st.session_state:
    st.session_state.editor_key = 0

# Initialize DataFrame in session state
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# Custom CSS for table width and height
st.markdown("""
    <style>
        .block-container {
            width: 100%;
            max-width: 100%;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .stDataFrame {
            width: 100%;
            max-width: 100%;
            height: calc(100vh - 300px) !important;
        }
        .stDataFrame > div {
            width: 100%;
            max-width: 100%;
            height: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Purview Unified Catalog Curator Portal")
[tab1, tab2, tab3, tab4] = st.tabs(["Data Assets", "Add Tags", "Delete Tags", "Add Data Owner / Expert"])

with tab1:
    # Use the DataFrame from session state
    df = st.session_state.df
    
    # Add search bar
    search_query = st.text_input("Search in all columns:", "")
    
    # Filter dataframe based on search query
    if search_query:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        df = df[mask]
    
    # Add a selection column
    df_with_selection = df.copy()
    df_with_selection.insert(0, 'Select', False)
    
    # Initialize select all state
    if 'select_all' not in st.session_state:
        st.session_state.select_all = False
    
    # Add Select All button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Select All"):
            st.session_state.select_all = not st.session_state.select_all
            # Force a rerun to update the selection
            st.rerun()
    
    # Apply select all state to all rows
    if st.session_state.select_all:
        df_with_selection['Select'] = True
    
    # Use st.data_editor for row selection
    edited_df = st.data_editor(
        df_with_selection,
        use_container_width=True,
        hide_index=True,
        key=f"data_editor_{st.session_state.editor_key}",
        num_rows="fixed",
        height=600,
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select rows",
                default=st.session_state.select_all,
            )
        },
        disabled=['id', 'name', 'contact', 'tag', 'classification', 'description']  # Disable editing of data columns
    )
    
    # Get selected rows and extract IDs
    selected_rows = edited_df[edited_df['Select'] == True]
    current_selected_ids = selected_rows['id'].tolist()
    
    # Print debug information
    st.write(f"Total rows in DataFrame: {len(df)}")
    st.write(f"Selected rows count: {len(selected_rows)}")
    st.write(f"Selected IDs count: {len(current_selected_ids)}")
    
    # Update session state with current selection
    st.session_state.selected_ids = current_selected_ids
    
    # Update the DataFrame in session state
    st.session_state.df = df
    
    # Display selected IDs below the table
    if st.session_state.selected_ids:
        st.markdown("---")
        st.subheader("Selected Items")
        
        # Create a simplified container for selected IDs
        st.markdown("""
            <style>
                .selected-items {
                    background-color: #ffffff;
                    padding: 15px;
                    border: 1px solid #e0e0e0;
                    margin: 10px 0;
                    display: flex;
                    flex-direction: row;
                    gap: 8px;
                    align-items: center;
                    overflow-x: auto;
                    white-space: nowrap;
                    -webkit-overflow-scrolling: touch;
                }
                .selected-id {
                    display: inline-block;
                    background-color: #f5f5f5;
                    padding: 8px 12px;
                    margin: 0;
                    font-size: 13px;
                    color: #333;
                    border: 1px solid #e0e0e0;
                    font-family: monospace;
                    flex-shrink: 0;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="selected-items">', unsafe_allow_html=True)
        for id in st.session_state.selected_ids:
            st.markdown(f'<div class="selected-id">{id}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.caption(f"Total selected: {len(st.session_state.selected_ids)} items")
        
        # Clear selection button
        if st.button("Clear Selection"):
            st.session_state.selected_ids = []
            st.session_state.editor_key += 1  # Force rerun with new key
            refresh_page()

with tab2:
    st.subheader("Add Tags to Selected Assets")
    
    if st.session_state.selected_ids:
        st.write(f"Selected assets for tagging: {len(st.session_state.selected_ids)}")

        # Display selected IDs and their tags
        st.markdown("""
            <style>
                .selected-items {
                    background-color: #f0f2f6;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 10px 0;
                }
                .selected-item {
                    display: flex;
                    align-items: center;
                    margin: 5px 0;
                    gap: 10px;
                }
                .selected-id {
                    display: inline-block;
                    background-color: #ffffff;
                    padding: 8px 15px;
                    border-radius: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    font-size: 14px;
                    min-width: 200px;
                }
                .selected-tags {
                    display: flex;
                    gap: 5px;
                    flex-wrap: wrap;
                }
                .tag {
                    display: inline-block;
                    background-color: #e3f2fd;
                    padding: 4px 10px;
                    border-radius: 15px;
                    font-size: 12px;
                    color: #1976d2;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="selected-items">', unsafe_allow_html=True)
        for id in st.session_state.selected_ids:
            # Get tags for this ID from the dataframe
            asset_tags = df[df['id'] == id]['tag'].iloc[0]
            tags_html = ""
            if pd.notna(asset_tags) and asset_tags:
                tags = eval(asset_tags) if isinstance(asset_tags, str) else asset_tags
                tags_html = '<div class="selected-tags">' + ''.join([f'<span class="tag">{tag}</span>' for tag in tags]) + '</div>'
            
            st.markdown(f'''
                <div class="selected-item">
                    <span class="selected-id">{id}</span>
                    {tags_html}
                </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add tag input section
        st.markdown("---")
        st.subheader("Add New Tags")
        
        # Tag input
        new_tag = st.text_input("Enter new tag:", placeholder="e.g., PII, Confidential, etc.")
        
        if st.button("Add Tag to Selected Assets"):
            if new_tag:
                st.success(f"Tag '{new_tag}' added to {len(st.session_state.selected_ids)} assets!")
                add_tag.main(guid=st.session_state.selected_ids,tag=new_tag)
                print(new_tag)
                print(st.session_state.selected_ids)
                # Here you would typically call your API or function to add the tag
                # Clear the input field after successful addition
                # Refresh the DataFrame in session state
                st.session_state.df = load_data()
                refresh_page()
            else:
                st.error("Please enter a tag name")
    else:
        st.info("Please select assets from the Data Assets tab to add tags")
        st.markdown("""
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #2196F3;">
                <p>To add tags:</p>
                <ol>
                    <li>Go to the Data Assets tab</li>
                    <li>Select the assets you want to tag using the checkboxes</li>
                    <li>Return to this tab to add tags</li>
                </ol>
            </div>
        """, unsafe_allow_html=True)

with tab3:
    st.subheader("Delete all tags")
    
    if st.session_state.selected_ids:
        st.write(f"Selected assets for tag deletion: {len(st.session_state.selected_ids)}")

        # Display selected IDs and their tags
        st.markdown("""
            <style>
                .selected-items {
                    background-color: #f0f2f6;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 10px 0;
                }
                .selected-item {
                    display: flex;
                    align-items: center;
                    margin: 5px 0;
                    gap: 10px;
                }
                .selected-id {
                    display: inline-block;
                    background-color: #ffffff;
                    padding: 8px 15px;
                    border-radius: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    font-size: 14px;
                    min-width: 200px;
                }
                .selected-tags {
                    display: flex;
                    gap: 5px;
                    flex-wrap: wrap;
                }
                .tag {
                    display: inline-block;
                    background-color: #e3f2fd;
                    padding: 4px 10px;
                    border-radius: 15px;
                    font-size: 12px;
                    color: #1976d2;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="selected-items">', unsafe_allow_html=True)
        for id in st.session_state.selected_ids:
            # Get tags for this ID from the dataframe
            asset_tags = df[df['id'] == id]['tag'].iloc[0]
            tags_html = ""
            if pd.notna(asset_tags) and asset_tags:
                tags = eval(asset_tags) if isinstance(asset_tags, str) else asset_tags
                tags_html = '<div class="selected-tags">' + ''.join([f'<span class="tag">{tag}</span>' for tag in tags]) + '</div>'
            
            st.markdown(f'''
                <div class="selected-item">
                    <span class="selected-id">{id}</span>
                    {tags_html}
                </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add tag input section
        st.markdown("---")
        st.subheader("Delete all tags")
        
        # Check if any tags exist in the selected assets
        has_tags = False
        for id in st.session_state.selected_ids:
            asset_row = df[df['id'] == id]
            if not asset_row.empty:
                tag_column = None
                for col in ['attributes_tag', 'tag', 'tags']:
                    if col in asset_row.columns:
                        tag_column = col
                        break
                
                if tag_column:
                    asset_tags = asset_row[tag_column].iloc[0]
                    if pd.notna(asset_tags) and asset_tags:
                        has_tags = True
                        break
        
        if has_tags:
            if st.button("Delete All Tags"):
                # Collect tags for each selected ID
                all_asset_tags = []
                for id in st.session_state.selected_ids:
                    # Get the row for this ID
                    asset_row = df[df['id'] == id]
                    if not asset_row.empty:
                        # Try different possible column names for tags
                        tag_column = None
                        for col in ['attributes_tag', 'tag', 'tags']:
                            if col in asset_row.columns:
                                tag_column = col
                                break
                        
                        if tag_column:
                            asset_tags = asset_row[tag_column].iloc[0]
                            if pd.notna(asset_tags) and asset_tags:
                                try:
                                    tags = eval(asset_tags) if isinstance(asset_tags, str) else asset_tags
                                    if isinstance(tags, list):
                                        all_asset_tags.extend(tags)
                                    else:
                                        all_asset_tags.append(str(tags))
                                except:
                                    # If eval fails, treat as a single tag
                                    all_asset_tags.append(str(asset_tags))
                
                # Remove duplicates while preserving order
                all_asset_tags = list(dict.fromkeys(all_asset_tags))
                
                if all_asset_tags:
                    delete_tag.main(guids=st.session_state.selected_ids, tags=all_asset_tags)
                    st.success(f"Deleted tags from {len(st.session_state.selected_ids)} assets!")
                    # Refresh the DataFrame in session state
                    st.session_state.df = load_data()
                    refresh_page()
        else:
            st.error("No tags exist in the selected assets")
    else:
        st.info("Please select assets from the Data Assets tab to remove all tags")
        st.markdown("""
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #2196F3;">
                <p>To add tags:</p>
                <ol>
                    <li>Go to the Data Assets tab</li>
                    <li>Select the assets you want to delete the tags</li>
                    <li>Return to this tab to execute script</li>
                </ol>
            </div>
        """, unsafe_allow_html=True)

with tab4:
    # Check if we need to reset tab4
    if st.session_state.tab4_reset:
        st.session_state.selected_owners = []
        st.session_state.selected_owner_ids = []
        st.session_state.current_selected_owners = []
        st.session_state.owner_comments = ""
        st.session_state.owner_role = "Owner"
        st.session_state.tab4_reset = False
    
    # Display success message if it exists
    if st.session_state.success_message:
        st.success(st.session_state.success_message)
        st.session_state.success_message = None  # Clear the message after displaying
    
    st.subheader("Add Data Owner")
    
    # Display selected assets from tab1
    if st.session_state.selected_ids:
        pass
    else:
        st.info("Please select assets from the Data Assets tab to add data owners")
        st.markdown("""
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 10px; border-left: 5px solid #2196F3;">
                <p>To add data owners:</p>
                <ol>
                    <li>Go to the Data Assets tab</li>
                    <li>Select the assets you want to add data owners to</li>
                    <li>Return to this tab to select data owners</li>
                </ol>
            </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    # Get users from get_entra_id_users using asyncio
    async def get_users():
        return await get_entra_id_users.main()
    
    # Run the async function
    users_df = asyncio.run(get_users())
    
    if users_df is not None and not users_df.empty:
        # Try to find the correct column name for names
        name_column = None
        possible_name_columns = ['name', 'displayName', 'userPrincipalName', 'givenName']
        
        for col in possible_name_columns:
            if col in users_df.columns:
                name_column = col
                break
        
        if name_column:
            # Add search bar for users
            search_query = st.text_input("Search users:", "")
            
            # Add spacing between search bar and data editor
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Filter users based on search
            if search_query:
                mask = users_df[name_column].astype(str).str.contains(search_query, case=False)
                filtered_df = users_df[mask].copy()  # Create an explicit copy
            else:
                filtered_df = users_df.copy()  # Create an explicit copy
            
            # Add Select column using .loc
            filtered_df.loc[:, 'Select'] = False
            
            # Display the filtered users with checkboxes
            edited_df = st.data_editor(
                filtered_df[['Select', name_column]],  # Reordered columns to put Select first
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select users",
                        default=False,
                    )
                }
            )
            
            # Get selected users and their IDs
            selected_mask = edited_df['Select'] == True
            selected_users = edited_df[selected_mask][name_column].tolist()
            
            # Update current selected owners
            st.session_state.current_selected_owners = selected_users
            
            # Get the corresponding IDs from the original dataframe
            selected_ids = []
            for user in selected_users:
                # Get the ID from the original dataframe where the name matches
                user_row = users_df[users_df[name_column] == user]
                if not user_row.empty:
                    user_id = user_row['id'].iloc[0]  # Use the 'id' column instead of index
                    selected_ids.append(user_id)
            
            if selected_users:
                st.markdown("---")
                st.subheader("Selected Users")
                st.markdown('<div class="selected-items">', unsafe_allow_html=True)
                for user in selected_users:
                    st.markdown(f'<div class="selected-item"><span class="selected-user">{user}</span></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Display selected assets from tab1
                if st.session_state.selected_ids:
                    st.markdown("---")
                    st.subheader("Selected Assets")
                    st.write(f"Selected assets for adding data owner: {len(st.session_state.selected_ids)}")
                    
                    # Display selected IDs in a nice format
                    st.markdown("""
                        <style>
                            .selected-items {
                                background-color: #f0f2f6;
                                padding: 15px;
                                border-radius: 10px;
                                margin: 10px 0;
                            }
                            .selected-item {
                                display: flex;
                                align-items: center;
                                margin: 5px 0;
                                gap: 10px;
                            }
                            .selected-id {
                                display: inline-block;
                                background-color: #ffffff;
                                padding: 8px 15px;
                                border-radius: 20px;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                font-size: 14px;
                                min-width: 200px;
                            }
                            .selected-user {
                                display: inline-block;
                                background-color: #e3f2fd;
                                padding: 8px 15px;
                                border-radius: 20px;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                font-size: 14px;
                                color: #1976d2;
                            }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('<div class="selected-items">', unsafe_allow_html=True)
                    for id in st.session_state.selected_ids:
                        st.markdown(f'<div class="selected-item"><span class="selected-id">{id}</span></div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Add role selection
                st.markdown("---")
                st.subheader("Role Selection")
                role = st.radio(
                    "Select the role for the users:",
                    ["Owner", "Expert"],
                    index=0 if st.session_state.owner_role == "Owner" else 1
                )
                st.session_state.owner_role = role
                
                # Add comments section
                st.markdown("---")
                st.subheader("Comments")
                comments = st.text_area("Add notes about the data expert / owner assignment:", 
                                      value=st.session_state.owner_comments,
                                      height=100)
                st.session_state.owner_comments = comments
                
                if st.button("Assign Selected Users as Data Expert / Owners"):
                    # Update the selected owners and their IDs in session state
                    st.session_state.selected_owners = st.session_state.current_selected_owners
                    st.session_state.selected_owner_ids = selected_ids
                    print(st.session_state.selected_owners)
                    print(st.session_state.selected_owner_ids)
                    print(st.session_state.owner_role)
                    print(st.session_state.owner_comments)
                    print(st.session_state.selected_ids)
                    
                    # Process each selected owner for each selected asset
                    for asset_id in st.session_state.selected_ids:
                        # Get the asset type from the dataframe
                        asset_row = st.session_state.df[st.session_state.df['id'] == asset_id]
                        if not asset_row.empty:
                            asset_type = asset_row['type'].iloc[0] if 'type' in asset_row.columns else "Asset"
                            
                            for owner_id in st.session_state.selected_owner_ids:
                                contact = st.session_state.owner_role
                                guid = asset_id
                                id = owner_id
                                notes = st.session_state.owner_comments
                                
                                try:
                                    add_owner.main(contact, guid, id, notes, asset_type)
                                except Exception as e:
                                    st.error(f"Error assigning owner {owner_id} to asset {asset_id}: {str(e)}")
                        else:
                            st.error(f"Could not find asset type for {asset_id}")
                    
                    st.session_state.success_message = f"Assigned {len(selected_users)} users as {st.session_state.owner_role}s to {len(st.session_state.selected_ids)} assets!"
                    # Refresh the DataFrame in session state
                    st.session_state.df = load_data()
                    # Clear the selection
                    st.session_state.selected_ids = []
                    st.session_state.selected_owners = []
                    st.session_state.selected_owner_ids = []
                    st.session_state.current_selected_owners = []
                    st.session_state.owner_comments = ""
                    # Force a rerun to update the UI
                    st.rerun()
        else:
            st.error(f"Could not find name column. Available columns are: {users_df.columns.tolist()}")
    else:
        st.error("No users found or error retrieving users")
        
# Add tab change detection
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "Data Assets"

# Check if tab has changed
if st.session_state.current_tab != "Add Data Owner" and tab4.active:
    st.session_state.tab4_reset = True

# Update current tab
if tab1.active:
    st.session_state.current_tab = "Data Assets"
elif tab2.active:
    st.session_state.current_tab = "Add Tags"
elif tab3.active:
    st.session_state.current_tab = "Delete Tags"
elif tab4.active:
    st.session_state.current_tab = "Add Data Owner"
        
        