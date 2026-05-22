from pydantic import BaseModel

class ReactionBase(BaseModel):
    reaction_name: str = ""
    equation: str
    reactants: str = ""
    products: str = ""
    conditions: str = ""
    catalysts: str = ""
    solvents: str = ""
    temperature: str = ""
    pressure: str = ""
    states: str = ""
    approved: bool = True
    hidden: bool = False

class ReactionIn(ReactionBase):
    pass

class ReactionOut(ReactionBase):
    id: int
    canonical_equation: str = ""
    reaction_kind: str = ""
    impossible_note: str = ""
    source_pdf: str = ""
    source_page: int = 0
    confidence_score: float = 0.9
    origin: str = "manual"
    class Config:
        from_attributes = True

class JobOut(BaseModel):
    id: int
    filename: str
    status: str
    message: str = ""
    total_pages: int = 0
    processed_pages: int = 0
    progress_percent: int = 0
    class Config:
        from_attributes = True

class JobReactionIn(BaseModel):
    reaction_name: str = ""
    equation: str
    reactants: str = ""
    products: str = ""
    conditions: str = ""
    catalysts: str = ""
    solvents: str = ""
    temperature: str = ""
    pressure: str = ""
    states: str = ""
    selected: bool = True

class JobReactionOut(JobReactionIn):
    id: int
    job_id: int
    canonical_equation: str = ""
    source_pdf: str = ""
    source_page: int = 0
    confidence_score: float = 0.9
    published: bool = False
    review_reason: str = ""
    internet_status: str = ""
    internet_note: str = ""
    class Config:
        from_attributes = True

class AdminLoginIn(BaseModel):
    password: str

class AdminLoginOut(BaseModel):
    ok: bool
    token: str

class FeedbackIn(BaseModel):
    original_text: str = ""
    wrong_result: str = ""
    correct_result: str = ""
    note: str = ""

class AdvertisementIn(BaseModel):
    placement: str = "main"
    title: str = ""
    html: str = ""
    active: bool = True

class AdvertisementOut(AdvertisementIn):
    id: int
    class Config:
        from_attributes = True
