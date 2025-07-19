# SQLAlchemy models for the Canadian Nutrient File (2015)
from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Food(Base):
    __tablename__ = 'food'
    food_id = Column(Integer, primary_key=True)
    food_code = Column(String)
    food_group_id = Column(Integer, ForeignKey('food_group.food_group_id'))
    food_source_id = Column(Integer, ForeignKey('food_source.food_source_id'))
    description = Column(String)
    description_fr = Column(String)
    country_code = Column(String)
    date_of_entry = Column(Date)
    date_of_publication = Column(Date)
    scientific_name = Column(String)

    food_group = relationship("FoodGroup")
    food_source = relationship("FoodSource")

class FoodGroup(Base):
    __tablename__ = 'food_group'
    food_group_id = Column(Integer, primary_key=True)
    code = Column(String)
    name = Column(String)
    name_fr = Column(String)

class FoodSource(Base):
    __tablename__ = 'food_source'
    food_source_id = Column(Integer, primary_key=True)
    code = Column(String)
    description = Column(String)
    description_fr = Column(String)

class NutrientName(Base):
    __tablename__ = 'nutrient_name'
    nutrient_name_id = Column(Integer, primary_key=True)
    code = Column(String)
    symbol = Column(String)
    unit = Column(String)
    name = Column(String)
    name_fr = Column(String)
    tagname = Column(String)
    decimals = Column(Integer)

class NutrientSource(Base):
    __tablename__ = 'nutrient_source'
    nutrient_source_id = Column(Integer, primary_key=True)
    code = Column(String)
    description = Column(String)
    description_fr = Column(String)

class NutrientAmount(Base):
    __tablename__ = 'nutrient_amount'
    id = Column(Integer, primary_key=True)
    food_id = Column(Integer, ForeignKey('food.food_id'))
    nutrient_name_id = Column(Integer, ForeignKey('nutrient_name.nutrient_name_id'))
    nutrient_source_id = Column(Integer, ForeignKey('nutrient_source.nutrient_source_id'))
    value = Column(Float)
    standard_error = Column(Float)
    num_observations = Column(Integer)
    date_of_entry = Column(Date)

class MeasureName(Base):
    __tablename__ = 'measure_name'
    measure_id = Column(Integer, primary_key=True)
    name = Column(String)
    name_fr = Column(String)

class ConversionFactor(Base):
    __tablename__ = 'conversion_factor'
    id = Column(Integer, primary_key=True)
    food_id = Column(Integer, ForeignKey('food.food_id'))
    measure_id = Column(Integer, ForeignKey('measure_name.measure_id'))
    value = Column(Float)
    date_of_entry = Column(Date)

class RefuseName(Base):
    __tablename__ = 'refuse_name'
    refuse_id = Column(Integer, primary_key=True)
    name = Column(String)
    name_fr = Column(String)

class RefuseAmount(Base):
    __tablename__ = 'refuse_amount'
    id = Column(Integer, primary_key=True)
    food_id = Column(Integer, ForeignKey('food.food_id'))
    refuse_id = Column(Integer, ForeignKey('refuse_name.refuse_id'))
    amount = Column(Float)
    date_of_entry = Column(Date)

class YieldName(Base):
    __tablename__ = 'yield_name'
    yield_id = Column(Integer, primary_key=True)
    name = Column(String)
    name_fr = Column(String)

class YieldAmount(Base):
    __tablename__ = 'yield_amount'
    id = Column(Integer, primary_key=True)
    food_id = Column(Integer, ForeignKey('food.food_id'))
    yield_id = Column(Integer, ForeignKey('yield_name.yield_id'))
    amount = Column(Float)
    date_of_entry = Column(Date)
