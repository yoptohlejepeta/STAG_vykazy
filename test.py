import streamlit as st
import pandas as pd
import io

# buffer to use for excel writer
buffer = io.BytesIO()

data = {
    "calories": [420, 380, 390],
    "duration": [50, 40, 45],
    "random1": [5, 12, 1],
    "random2": [230, 23, 1]
}
df = pd.DataFrame(data)

@st.cache
def convert_to_csv(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv(index=False).encode('utf-8')

csv = convert_to_csv(df)

# display the dataframe on streamlit app
st.write(df)

# download button 1 to download dataframe as csv
download1 = st.download_button(
    label="Download data as CSV",
    data=csv,
    file_name='large_df.csv',
    mime='text/csv'
)

# download button 2 to download dataframe as xlsx
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # Write each dataframe to a different worksheet.
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    # Close the Pandas Excel writer and output the Excel file to the buffer
    writer.save()

    download2 = st.download_button(
        label="Download data as Excel",
        data=buffer,
        file_name='large_df.xlsx',
        mime='application/vnd.ms-excel'
    )