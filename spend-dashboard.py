import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px

st.sidebar.markdown(
""" 
# SafeGraph Spend by brand :credit_card: 
### Quick stats on Spend brand coverage

All data pulled from Snowflake.

*Note: The first connection takes ~30 seconds to initiate, but subsequent brand selections should happen locally (<10s).*
"""
)

# Functions for pulling data from Snowflake
# Initialize connection.
# Uses st.cache to only run once.
@st.cache(allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None,"builtins.weakref": lambda _: None,})
def init_connection():
    return snowflake.connector.connect(**st.secrets["snowflake"])

conn = init_connection()

# Perform query.
# Uses st.cache to only rerun when the query changes
@st.cache(hash_funcs={"_thread.lock": lambda _: None})
def get_safegraph_data_from_snowflake(query):
    return pd.read_sql(query, conn)

# Populate brands list
@st.cache(hash_funcs={"_thread.lock": lambda _: None})
def populate_brands_list():
    brand_query = f'''
    SELECT DISTINCT brands
    FROM SG_SPEND_CORE.PUBLIC.CORE_POI_SPEND
    WHERE date_range_start BETWEEN '2021-09-01' AND '2021-10-01'
    ORDER BY brands
    '''
    return get_safegraph_data_from_snowflake(brand_query)

# Sidebar options
brands = populate_brands_list()
brand_option = st.sidebar.selectbox('Select a SafeGraph brand', brands)

# Main app body

# Query for coverage numbers
q_coverage = f'''
WITH core AS (
  SELECT *
  FROM SG_CORE_PLACES_US.PUBLIC.CORE_POI
),
patterns AS (
  SELECT *
  FROM SG_PATTERNS_US.PUBLIC.PATTERNS
  WHERE date_range_start BETWEEN '2021-09-01' AND '2021-10-01'
),
spend AS (
  SELECT *
  FROM SG_SPEND_CORE.PUBLIC.CORE_POI_SPEND
  WHERE date_range_start BETWEEN '2021-09-01' AND '2021-10-01'
)
SELECT 
    COUNT(spend.placekey) as spend_placekeys,
    COUNT(patterns.placekey) as patterns_placekeys,
    COUNT(core.placekey) as core_placekeys
FROM 
(core LEFT JOIN patterns ON core.placekey = patterns.placekey)
LEFT JOIN spend ON core.placekey = spend.placekey
WHERE core.brands LIKE '%{brand_option.replace("'","''")}%'
'''
coverage_df = get_safegraph_data_from_snowflake(q_coverage)
coverage_df = coverage_df.transpose().rename({0:'Number'},axis=1)
coverage_df['Coverage'] = coverage_df['Number'] / coverage_df.loc['CORE_PLACEKEYS','Number']

# Query for Spend data
q_data = f'''
SELECT *
FROM SG_SPEND_CORE.PUBLIC.CORE_POI_SPEND
WHERE date_range_start BETWEEN '2021-09-01' AND '2021-10-01'
AND brands LIKE '%{brand_option.replace("'","''")}%'
'''
df = get_safegraph_data_from_snowflake(q_data)

# High level stats
st.markdown(f"There are **{len(df)}** POIs with the brand **{brand_option}**  in Spend in Sept 2021. (`BRANDS LIKE '%{brand_option}%'`)")
st.markdown(f'''
    This is **{100*coverage_df.loc['SPEND_PLACEKEYS','Coverage']:.0f}%** of {brand_option} POIs in Core
    (By comparison, there are **{100*coverage_df.loc['PATTERNS_PLACEKEYS','Coverage']:.0f}%** with Patterns).
    ''')
st.write(coverage_df)

#Show table of raw data
if st.sidebar.checkbox('Show Spend rows',value=True):
    st.markdown('**Spend rows (with Core joined)**')
    st.dataframe(df)

#Show histogram of num_transactions
if st.sidebar.checkbox('Show Num Transaction histogram',value=True):
    f = px.histogram(df, x="RAW_NUM_TRANSACTIONS", nbins=15,title='POI Num Transactions histogram',
                        color_discrete_sequence=['lightblue'])
    f.update_xaxes(title="Number of Transactions joined to the POI")
    f.update_yaxes(title="Number of POIs")
    st.plotly_chart(f)

#Show histogram of transaction size
if st.sidebar.checkbox('Show Transaction Size histogram',value=True):
    f = px.histogram(df, x="MEDIAN_SPEND_PER_TRANSACTION", nbins=15,title='Transaction Size histogram',
                        color_discrete_sequence=['lightblue'])
    f.update_xaxes(title="Median Spend Per Transaction")
    f.update_yaxes(title="Number of POIs")
    st.plotly_chart(f)