import pytest
from src.tools.calculators import calculate_heart_score, calculate_curb65_score, calculate_wells_pe_score, calculate_bmi


@pytest.mark.parametrize('age,points', [(44,0),(45,1),(64,1),(65,2)])
def test_heart_age_boundaries(age, points):
    result = calculate_heart_score(0,0,age,0,0)
    assert result.value == points
    assert result.details['review_status'] == 'PENDING_CLINICAL_REVIEW'
    assert result.details['source'].startswith('https://')


@pytest.mark.parametrize('value', [True,-1,3,1.5,float('nan'),float('inf'),'1'])
def test_invalid_heart_categories_are_rejected(value):
    with pytest.raises(ValueError):
        calculate_heart_score(value,0,40,0,0)


@pytest.mark.parametrize('value', [None,0,1,'false','true'])
def test_wells_requires_actual_booleans(value):
    with pytest.raises(ValueError):
        calculate_wells_pe_score(value,False,False,False,False,False,False)


@pytest.mark.parametrize('inputs,total,label', [
    ((True,False,False,False,False,True,False),4,'PE unlikely'),
    ((True,False,True,False,False,False,False),4.5,'PE likely'),
    ((True,True,True,True,True,True,True),12.5,'PE likely')])
def test_wells_two_level_boundary_and_complete_provenance(inputs,total,label):
    result = calculate_wells_pe_score(*inputs)
    assert result.value == total
    assert result.interpretation.startswith(label)
    assert all(k in result.details for k in ['immobilization_surgery','previous_dvt_pe','hemoptysis','malignancy'])
    assert '%' not in result.interpretation


@pytest.mark.parametrize('rr,sys,dia,age,total', [(29,90,61,64,0),(30,90,61,64,1),
    (29,89,61,64,1),(29,90,60,64,1),(29,89,60,64,1),(29,90,61,65,1)])
def test_curb_non_laboratory_boundaries(rr,sys,dia,age,total):
    result = calculate_curb65_score(False,0,rr,sys,dia,age)
    assert result.value == total
    assert '%' not in result.interpretation
    assert 'Treatment' not in result.interpretation


@pytest.mark.parametrize('value', [True,-1,float('nan'),float('inf'),'20'])
def test_curb_rejects_invalid_measurements(value):
    with pytest.raises(ValueError):
        calculate_curb65_score(False,value,20,120,80,50)


@pytest.mark.parametrize('weight,height', [(True,1.7),(70,False),(float('inf'),1.7),(70,0),(-1,1.7)])
def test_bmi_rejects_invalid_measurements(weight,height):
    with pytest.raises(ValueError):
        calculate_bmi(weight,height)
