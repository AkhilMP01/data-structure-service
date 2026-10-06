from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..database import get_session
from ..models import DataElement, Dataset, DataType
from ..schemas import (
    DataElementCreate,
    DataElementRead,
    DatasetCreate,
    DatasetRead,
    DatasetReadWithElements,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
def create_dataset(payload: DatasetCreate, session: Session = Depends(get_session)):
    dataset = Dataset(name=payload.name, description=payload.description)
    session.add(dataset)
    try:
        session.commit()
    except IntegrityError:
        # unique(name) violated -> return a clean 409 instead of a 500
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A dataset named '{payload.name}' already exists.",
        )
    session.refresh(dataset)
    return dataset


@router.get("", response_model=list[DatasetRead])
def list_datasets(session: Session = Depends(get_session)):
    return session.exec(select(Dataset).order_by(Dataset.id)).all()


@router.get("/{dataset_id}", response_model=DatasetReadWithElements)
def get_dataset(dataset_id: int, session: Session = Depends(get_session)):
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")
    return dataset


@router.post(
    "/{dataset_id}/elements",
    response_model=DataElementRead,
    status_code=status.HTTP_201_CREATED,
)
def add_data_element(
    dataset_id: int,
    payload: DataElementCreate,
    session: Session = Depends(get_session),
):
    # check the parent exists first so we get a clean 404, not an FK error
    if session.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")

    element = DataElement(
        dataset_id=dataset_id,
        name=payload.name,
        data_type=payload.data_type,
        description=payload.description,
        is_required=payload.is_required,
        is_pii=payload.is_pii,
    )
    session.add(element)
    try:
        session.commit()
    except IntegrityError:
        # unique(dataset_id, name) violated
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Data element '{payload.name}' already exists in dataset {dataset_id}.",
        )
    session.refresh(element)
    return element


@router.get("/{dataset_id}/elements", response_model=list[DataElementRead])
def list_data_elements(
    dataset_id: int,
    session: Session = Depends(get_session),
    data_type: DataType | None = Query(default=None),
    is_pii: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="match on element name"),
):
    if session.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")

    query = select(DataElement).where(DataElement.dataset_id == dataset_id)
    if data_type is not None:
        query = query.where(DataElement.data_type == data_type)
    if is_pii is not None:
        query = query.where(DataElement.is_pii == is_pii)
    if search:
        query = query.where(DataElement.name.ilike(f"%{search}%"))

    return session.exec(query.order_by(DataElement.id)).all()
