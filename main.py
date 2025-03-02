from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi_pagination import Page, paginate
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, joinedload
from sqlalchemy.exc import IntegrityError

# Configuração do Banco de Dados (SQLite para demonstração)
DATABASE_URL = "sqlite:///./atleta.db"  # Use um banco de dados mais robusto em produção (PostgreSQL, MySQL, etc.)

engine = create_engine(DATABASE_URL)
Base = declarative_base()


# Modelo de Dados
class CentroTreinamento(Base):
    __tablename__ = "centros_treinamento"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    endereco = Column(String)

    atletas = relationship("Atleta", back_populates="centro_treinamento")


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    descricao = Column(String, nullable=True)  # Permitir descrições nulas

    atletas = relationship("Atleta", back_populates="categoria")


class Atleta(Base):
    __tablename__ = "atletas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    cpf = Column(String, unique=True, index=True)
    centro_treinamento_id = Column(Integer, ForeignKey("centros_treinamento.id"))
    categoria_id = Column(Integer, ForeignKey("categorias.id"))

    centro_treinamento = relationship("CentroTreinamento", back_populates="atletas")
    categoria = relationship("Categoria", back_populates="atletas")

    __table_args__ = (UniqueConstraint("cpf", name="unique_cpf"),)  # Garante CPF único


Base.metadata.create_all(bind=engine)


# Dependência para a Sessão do Banco de Dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Modelos Pydantic para Request e Response
class CentroTreinamentoCreate(BaseModel):
    nome: str
    endereco: str


class CentroTreinamentoResponse(BaseModel):
    id: int
    nome: str
    endereco: str

    model_config = ConfigDict(from_attributes=True)


class CategoriaCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None  # Permite descrição opcional


class CategoriaResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AtletaCreate(BaseModel):
    nome: str
    cpf: str
    centro_treinamento_id: int
    categoria_id: int


class AtletaResponse(BaseModel):
    id: int
    nome: str
    cpf: str
    centro_treinamento_id: int
    categoria_id: int

    model_config = ConfigDict(from_attributes=True)


class AtletaListResponse(BaseModel):
    nome: str
    centro_treinamento: str
    categoria: str

    model_config = ConfigDict(from_attributes=True)


# Inicialização da API FastAPI (MOVER ESTA LINHA PARA CIMA)
app = FastAPI()


# Adicione esta rota para resolver o erro 404 (AGORA FUNCIONARÁ)
@app.get("/")
async def read_root():
    return {"message": "Bem-vindo à API de Atletas!"}


# Rotas para Centro de Treinamento
@app.post(
    "/centros_treinamento/",
    response_model=CentroTreinamentoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_centro_treinamento(
    centro_treinamento: CentroTreinamentoCreate, db: Session = Depends(get_db)
):
    db_centro = CentroTreinamento(**centro_treinamento.dict())
    db.add(db_centro)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail=f"Já existe um centro de treinamento com o nome: {centro_treinamento.nome}",
        )
    db.refresh(db_centro)
    return db_centro


@app.get("/centros_treinamento/{centro_id}", response_model=CentroTreinamentoResponse)
def read_centro_treinamento(centro_id: int, db: Session = Depends(get_db)):
    db_centro = (
        db.query(CentroTreinamento).filter(CentroTreinamento.id == centro_id).first()
    )
    if db_centro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Centro de treinamento não encontrado",
        )
    return db_centro


@app.get("/centros_treinamento/", response_model=Page[CentroTreinamentoResponse])
def list_centros_treinamento(db: Session = Depends(get_db)):
    return paginate(db.query(CentroTreinamento))


# Rotas para Categorias
@app.post(
    "/categorias/",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_categoria(categoria: CategoriaCreate, db: Session = Depends(get_db)):
    db_categoria = Categoria(
        **categoria.dict(exclude_unset=True)
    )  # Usa exclude_unset para lidar com Optionals
    db.add(db_categoria)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail=f"Já existe uma categoria com o nome: {categoria.nome}",
        )
    db.refresh(db_categoria)
    return db_categoria


@app.get("/categorias/{categoria_id}", response_model=CategoriaResponse)
def read_categoria(categoria_id: int, db: Session = Depends(get_db)):
    db_categoria = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if db_categoria is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada"
        )
    return db_categoria


@app.get("/categorias/", response_model=Page[CategoriaResponse])
def list_categorias(db: Session = Depends(get_db)):
    return paginate(db.query(Categoria))


# Rotas para Atletas
@app.post(
    "/atletas/", response_model=AtletaResponse, status_code=status.HTTP_201_CREATED
)
def create_atleta(atleta: AtletaCreate, db: Session = Depends(get_db)):
    db_atleta = Atleta(**atleta.dict())
    db.add(db_atleta)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail=f"Já existe um atleta cadastrado com o cpf: {atleta.cpf}",
        )
    db.refresh(db_atleta)
    return db_atleta


@app.get("/atletas/{atleta_id}", response_model=AtletaResponse)
def read_atleta(atleta_id: int, db: Session = Depends(get_db)):
    db_atleta = db.query(Atleta).filter(Atleta.id == atleta_id).first()
    if db_atleta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Atleta não encontrado"
        )
    return db_atleta


@app.get("/atletas/", response_model=Page[AtletaListResponse])
def list_atletas(
    nome: Optional[str] = Query(None, description="Filtrar por nome do atleta"),
    cpf: Optional[str] = Query(None, description="Filtrar por CPF do atleta"),
    db: Session = Depends(get_db),
):
    """
    Lista atletas com suporte a paginação e filtros por nome e CPF.
    """
    query = db.query(Atleta).join(CentroTreinamento).join(Categoria)

    if nome:
        query = query.filter(Atleta.nome.ilike(f"%{nome}%"))  # Case-insensitive search
    if cpf:
        query = query.filter(Atleta.cpf == cpf)

    # Formata a resposta conforme o modelo AtletaListResponse
    def format_result(atleta: Atleta) -> AtletaListResponse:
        return AtletaListResponse(
            nome=atleta.nome,
            centro_treinamento=atleta.centro_treinamento.nome,
            categoria=atleta.categoria.nome,
        )

    atletas = query.options(
        joinedload(Atleta.centro_treinamento), joinedload(Atleta.categoria)
    ).all()
    # Paginate exige que a query seja executada dentro dele
    return paginate(atletas)


# Exemplos de uso (para testes)
#  Executar no terminal: uvicorn main:app --reload
#  Criar um centro de treinamento: POST /centros_treinamento com JSON: {"nome": "CT Bom Demais", "endereco": "Rua dos Atletas, 123"}
#  Criar uma categoria: POST /categorias com JSON: {"nome": "Iniciante"}
#  Criar um atleta: POST /atletas com JSON: {"nome": "João da Silva", "cpf": "123.456.789-00", "centro_treinamento_id": 1, "categoria_id": 1}
#  Listar atletas: GET /atletas?limit=10&offset=0
#  Listar atletas filtrando por nome: GET /atletas?nome=João
#  Listar atletas filtrando por cpf: GET /atletas?cpf=123.456.789-00

# Dependências adicionais:
# pip install fastapi uvicorn sqlalchemy pydantic python-multipart fastapi-pagination
