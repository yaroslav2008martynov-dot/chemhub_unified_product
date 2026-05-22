from pydantic import BaseModel

class ReactionIn(BaseModel):
    reaction_name: str = ""
    equation: str
    canonical_equation: str = ""
    reactants: str = ""
    products: str = ""
    conditions: str = ""
    catalysts: str = ""
    solvents: str = ""
    temperature: str = ""
    pressure: str = ""
    states: str = ""
    reaction_kind: str = ""
    impossible_note: str = ""
    source_pdf: str = ""
    source_page: int = 0
    confidence_score: float = 1.0
    validation_status: str = "manual"
    internet_status: str = "not_checked"
    internet_note: str = ""
    approved: bool = True
    hidden: bool = False

class ReactionOut(ReactionIn):
    id: int
    origin: str = "ai"
    class Config:
        from_attributes = True

class JobOut(BaseModel):
    id: int
    filename: str
    status: str
    progress_percent: int
    total_pages: int
    processed_pages: int
    message: str
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
    confidence_score: float = 0.0
    internet_status: str = "not_checked"
    internet_note: str = ""
    review_reason: str = ""
    published: bool = False
    class Config:
        from_attributes = True

class FeedbackIn(BaseModel):
    reaction_id: int = 0
    scope: str = "general"
    comment: str
    before_text: str = ""
    after_text: str = ""

class AdvertisementIn(BaseModel):
    placement: str
    title: str = ""
    html: str = ""
    active: bool = True

class AdvertisementOut(AdvertisementIn):
    id: int
    class Config:
        from_attributes = True

class AdminLoginIn(BaseModel):
    password: str

class AdminLoginOut(BaseModel):
    ok: bool
    token: str
