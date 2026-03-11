# 启动后端
export PYTHONPATH=backend:$PYTHONPATH
cd backend
uvicorn app.main:app --reload --port 8000 &
cd ..

# 启动前端
streamlit run frontend/streamlit_app.py