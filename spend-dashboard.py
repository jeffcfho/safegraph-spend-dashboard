import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.express as px

QUERY_CACHE_TTL =  3600 #1 hour

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
@st.cache(ttl=QUERY_CACHE_TTL, hash_funcs={"_thread.lock": lambda _: None})
def get_safegraph_data_from_snowflake(query):
    return pd.read_sql(query, conn)

# Populate brands list
@st.cache(hash_funcs={"_thread.lock": lambda _: None})
def populate_brands_list():
    brand_query = f'''
    SELECT DISTINCT brands, safegraph_brand_ids
    FROM SG_SPEND_CORE.PUBLIC.CORE_POI_SPEND
    WHERE date_range_start BETWEEN '2021-09-01' AND '2021-10-01'
    ORDER BY brands
    '''
    return pd.read_sql(brand_query, conn)

# Sidebar options
brands = populate_brands_list()
brand_option = st.sidebar.selectbox('Select a SafeGraph brand', brands)
brand_option_id = brands.loc[brands["BRANDS"]==brand_option,"SAFEGRAPH_BRAND_IDS"].values[0]

# Main app body

# Query for coverage numbers
q_coverage = f'''
WITH core AS (
  SELECT *
  FROM SG_CORE_PLACES_US.PUBLIC.CORE_POI
  WHERE closed_on IS NULL 
  OR closed_on >= '2021-09'
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
WHERE core.safegraph_brand_ids LIKE '%{brand_option_id}%'
'''
coverage_df = get_safegraph_data_from_snowflake(q_coverage)
coverage_df = coverage_df.transpose().rename({0:'Number'},axis=1)
coverage_df['Coverage'] = coverage_df['Number'] / coverage_df.loc['CORE_PLACEKEYS','Number']

# Query for Spend data
q_data = f'''
SELECT *
FROM SG_SPEND_CORE.PUBLIC.CORE_POI_SPEND
WHERE date_range_start BETWEEN '2021-09-01' AND '2021-10-01'
AND (closed_on IS NULL OR closed_on >= '2021-09') //Until we fix the spend to closed POI problem
AND safegraph_brand_ids LIKE '%{brand_option_id}%'
'''
df = get_safegraph_data_from_snowflake(q_data)

# High level stats
st.markdown(f"There are **{len(df)}** non-closed POIs with the brand **{brand_option}**  in Spend in Sept 2021. (`SAFEGRAPH_BRAND_IDS LIKE '%{brand_option_id}%'`)")
st.markdown(f'''
    This is **{100*coverage_df.loc['SPEND_PLACEKEYS','Coverage']:.0f}%** of {brand_option} non-closed POIs in Core
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