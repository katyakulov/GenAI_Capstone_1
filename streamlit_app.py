import logging
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from app.agent import answer_user
from app.db import init_if_missing, kpis, revenue_by_region, sample_rows
from app.tickets import create_github_issue, create_local_ticket

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
)
LOGGER = logging.getLogger('data-insights-app')

st.set_page_config(page_title='Data Insights App', page_icon='📊', layout='wide')
init_if_missing()

st.title('📊 Chat with Data — Data Insights App')
st.caption('GenAI assistant for safe, tool-based database insights. The full datasource is never sent to the model.')

with st.sidebar:
    st.header('Business context')
    data = kpis()
    st.metric('Customers', f"{data['customers']:,}")
    st.metric('Deals', f"{data['deals']:,}")
    st.metric('Support tickets', f"{data['support_tickets']:,}")
    st.metric('Won revenue', f"${data['won_revenue']:,.0f}")
    st.metric('Open deals', f"{data['open_deals']:,}")
    st.divider()
    st.subheader('Sample questions')
    st.markdown('- Which region has the highest won revenue?\n- Show top 5 customers by won deal value.\n- Compare revenue by product.\n- Create a support ticket for missing CRM access.')

col1, col2 = st.columns([1.2, 1])
with col1:
    st.subheader('Won revenue by region')
    rev_df = revenue_by_region()
    st.plotly_chart(px.bar(rev_df, x='region', y='won_revenue'), use_container_width=True)
with col2:
    st.subheader('Sample data preview')
    table = st.selectbox('Table', ['customers', 'deals', 'support_tickets'])
    st.dataframe(sample_rows(table), use_container_width=True)

st.divider()
st.subheader('Ask the agent')

if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

prompt = st.chat_input('Ask a business question about the database...')
if prompt:
    LOGGER.info('User prompt: %s', prompt)
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.markdown(prompt)

    with st.chat_message('assistant'):
        if not os.getenv('OPENAI_API_KEY'):
            answer = 'OPENAI_API_KEY is not configured. Add it to .env or Streamlit secrets, then restart the app.'
        else:
            answer = answer_user(st.session_state.messages)
        st.markdown(answer)
    st.session_state.messages.append({'role': 'assistant', 'content': answer})

st.divider()
with st.expander('Need human support? Create a ticket'):
    with st.form('support_ticket_form'):
        title = st.text_input('Title', placeholder='Example: Need help interpreting revenue anomaly')
        description = st.text_area('Description')
        priority = st.selectbox('Priority', ['low', 'medium', 'high', 'urgent'], index=1)
        submitted = st.form_submit_button('Create support ticket')
        if submitted:
            if not title or not description:
                st.error('Please provide title and description.')
            else:
                try:
                    result = create_github_issue(title, description, 'support')
                except Exception as exc:
                    LOGGER.exception('Ticket form GitHub creation failed: %s', exc)
                    result = create_local_ticket(title, description, priority)
                st.success(f'Ticket created: {result}')
