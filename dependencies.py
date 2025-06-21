from fastapi.security import HTTPBearer
from langchain_community.llms import LlamaCpp
from mailjet_rest import Client
from constants import MAILJET_API_KEY, MAILJET_SECRET_KEY

security = HTTPBearer()
mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')

llm = LlamaCpp(
    model_path="llms/solar-10.7b-instruct-v1.0.Q4_K_M.gguf",
    n_gpu_layers=-1,
    n_batch=512,
    n_ctx=16384,
    verbose=True,
)