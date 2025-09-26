from fastapi import APIRouter, HTTPException
from src.models.client import Client
from src.services.client_service import ClientService

router = APIRouter()
client_service = ClientService()

@router.post("/clients/", response_model=Client)
async def add_client(client: Client):
    if client_service.add_client(client):
        return client
    raise HTTPException(status_code=400, detail="Client could not be added")

@router.delete("/clients/{client_id}", response_model=dict)
async def remove_client(client_id: str):
    if client_service.remove_client(client_id):
        return {"detail": "Client removed successfully"}
    raise HTTPException(status_code=404, detail="Client not found")

@router.get("/clients/", response_model=list[Client])
async def list_clients():
    return client_service.list_clients()