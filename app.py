from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List

# Initialize FastAPI app
app = FastAPI()

# Database setup
DATABASE_URL = "sqlite:///./career_planning.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency function to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CareerGoal model for the database
class CareerGoal(Base):
    __tablename__ = 'career_goals'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    milestones = Column(String)  # Store milestones as a comma-separated string
    progress = Column(Float, default=0.0)  # Progress as a percentage
    estimated_days = Column(Integer)  # Estimated days to achieve the goal
    elapsed_days = Column(Integer, default=0)  # Track the number of days progressed

# Create database tables
Base.metadata.create_all(bind=engine)

# Pydantic models for request and response validation
class CareerGoalCreate(BaseModel):
    title: str
    description: str
    milestones: List[str]  # List of milestones to match Kivy's format
    progress: float = 0.0
    estimated_days: int

class CareerGoalResponse(BaseModel):
    id: int
    title: str
    description: str
    milestones: List[str]  # List of milestones
    progress: float
    estimated_days: int
    elapsed_days: int  # Include elapsed days in the response

    class Config:
        orm_mode = True

# Create a new career goal
@app.post("/goals/", response_model=CareerGoalResponse)
async def create_goal(goal: CareerGoalCreate, db: Session = Depends(get_db)):
    db_goal = CareerGoal(
        title=goal.title,
        description=goal.description,
        milestones=",".join(goal.milestones),  # Join the list into a comma-separated string
        progress=goal.progress,
        estimated_days=goal.estimated_days,
        elapsed_days=0  # Initialize elapsed days to 0
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

# Retrieve all career goals
@app.get("/goals/", response_model=List[CareerGoalResponse])
async def get_goals(db: Session = Depends(get_db)):
    goals = db.query(CareerGoal).all()
    return [
        CareerGoalResponse(
            id=goal.id,
            title=goal.title,
            description=goal.description,
            milestones=goal.milestones.split(",") if goal.milestones else [],  # Split back into a list
            progress=goal.progress,
            estimated_days=goal.estimated_days,
            elapsed_days=goal.elapsed_days,  # Include elapsed days in the response
        )
        for goal in goals
    ]

# Delete a career goal by ID
@app.delete("/goals/{goal_id}/")
async def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    db_goal = db.query(CareerGoal).filter(CareerGoal.id == goal_id).first()
    if db_goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(db_goal)
    db.commit()
    return {"message": "Goal deleted successfully"}

@app.put("/goals/{goal_id}/increment/")
async def increment_progress(goal_id: int, db: Session = Depends(get_db)):
    db_goal = db.query(CareerGoal).filter(CareerGoal.id == goal_id).first()
    if db_goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Increment the elapsed days and progress
    if db_goal.elapsed_days < db_goal.estimated_days:
        db_goal.elapsed_days += 1
        db_goal.progress = (db_goal.elapsed_days / db_goal.estimated_days) * 100

        # Check if progress reaches 100% and update accordingly
        if db_goal.elapsed_days >= db_goal.estimated_days:
            db_goal.progress = 100

        db.commit()
        db.refresh(db_goal)

        return {"updated_goal": {
            "id": db_goal.id,
            "title": db_goal.title,
            "description": db_goal.description,
            "milestones": db_goal.milestones.split(",") if db_goal.milestones else [],
            "progress": db_goal.progress,
            "estimated_days": db_goal.estimated_days,
            "elapsed_days": db_goal.elapsed_days
        }}
    else:
        raise HTTPException(status_code=400, detail="Goal already completed")

@app.patch("/goals/{goal_id}/increment/")  # Fix: Changed to PATCH as the original method used it
async def increment_goal_progress(goal_id: int, db: Session = Depends(get_db)):
    db_goal = db.query(CareerGoal).filter(CareerGoal.id == goal_id).first()
    if db_goal:
        db_goal.elapsed_days += 1  # Increase the elapsed days
        db_goal.progress = (db_goal.elapsed_days / db_goal.estimated_days) * 100  # Recalculate progress
        db.commit()
        db.refresh(db_goal)
        return {"message": "Progress updated", "goal": {
            "id": db_goal.id,
            "title": db_goal.title,
            "description": db_goal.description,
            "milestones": db_goal.milestones.split(",") if db_goal.milestones else [],
            "progress": db_goal.progress,
            "estimated_days": db_goal.estimated_days,
            "elapsed_days": db_goal.elapsed_days
        }}
    return {"message": "Goal not found"}

@app.put("/goals/{goal_id}/")
async def update_goal(goal_id: int, goal: CareerGoalCreate, db: Session = Depends(get_db)):
    db_goal = db.query(CareerGoal).filter(CareerGoal.id == goal_id).first()
    if db_goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Update all the goal attributes
    db_goal.title = goal.title
    db_goal.description = goal.description
    db_goal.milestones = ",".join(goal.milestones)  # Update milestones
    db_goal.estimated_days = goal.estimated_days  # Update estimated days
    db_goal.elapsed_days = 0  # Reset elapsed days since it's a full update (or handle as you prefer)

    db.commit()
    db.refresh(db_goal)

    return {"updated_goal": {
        "id": db_goal.id,
        "title": db_goal.title,
        "description": db_goal.description,
        "milestones": db_goal.milestones.split(",") if db_goal.milestones else [],
        "progress": db_goal.progress,
        "estimated_days": db_goal.estimated_days,
        "elapsed_days": db_goal.elapsed_days
    }}