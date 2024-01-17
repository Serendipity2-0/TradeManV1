import streamlit as st
import json
import os
from typing import Dict
from pydantic import BaseModel, Field
from typing import Dict, Optional


# Define the directory where JSON files are stored
json_directory = 'userjson'  # Update this path to your folder

# Define Pydantic model
class User(BaseModel):
    account_name: Optional[str] = Field(None)
    broker: Optional[str] = Field(None)
    username: Optional[str] = Field(None)
    password: Optional[str] = Field(None)
    api_key: Optional[str] = Field(None)
    api_secret: Optional[str] = Field(None)
    totp: Optional[str] = Field(None)
    percentage_risk: Optional[Dict[str, float]] = Field(None)

# Load JSON data into Pydantic model
def load_data(filepath):
    with open(filepath, "r") as file:
        data = json.load(file)
        user = User(**data)
    return user

# Save modified data back to JSON
def save_data(filepath, data):
    with open(filepath, "w") as file:
        json.dump(data, file, indent=4)

# Streamlit UI to select, view, and edit files
def main():
    st.title("Percentage Risk Editor")

    # List all JSON files in the directory
    json_files = [f for f in os.listdir(json_directory) if f.endswith('.json')]
    
    # Sidebar for selecting a file
    selected_file = st.sidebar.radio("Select a file to edit", json_files)
    file_path = os.path.join(json_directory, selected_file)

    # Display the name of the file being edited as a caption
    if selected_file:
        st.caption(f"Editing: {selected_file}")
        
        # Load data and create Pydantic model instance
        user_data = load_data(file_path)

        # Display and edit percentage_risk values
        if user_data.percentage_risk:
            st.subheader("Edit Strategies")
            for strategy, risk in user_data.percentage_risk.items():
                new_risk = st.number_input(f"{strategy}", value=risk, format="%.2f")
                user_data.percentage_risk[strategy] = new_risk
        else:
            st.write("No percentage_risk data available to edit.")

        # Button to save changes
        if st.button("Save Changes"):
            save_data(file_path, user_data.dict())
            st.success(f"Data saved to {selected_file}!")

if __name__ == "__main__":
    main()
