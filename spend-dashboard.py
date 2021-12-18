import streamlit as st
import pandas as pd
import plotly.express as px

""" 
# SafeGraph Spend :credit_card: 
### A dashboard for visualizing brand coverage


"""

# import data from snowflake
# @st.cache
# def load_data():
# 	""" Load data for displaying """
# 	u_list = pd.read_csv('../modeling_dfs/final_users_50k.csv')
# 	r_list = pd.read_csv('../notebooks/top20_products_recom_purchasedbefore.csv')
# 	p_list = pd.read_csv('../notebooks/top200_products.csv')
# 	p_list = p_list.loc[p_list['organic']==1]
# 	return u_list,r_list,p_list

# user_list,rec_list,prod_list = load_data()

st.markdown("## Brands")
# get coverage stats by brand
prod_option = st.selectbox('Select a SafeGraph brand', ("McDonald's", "Chipotle"))
