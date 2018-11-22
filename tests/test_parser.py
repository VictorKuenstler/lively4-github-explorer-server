import pytest

from server.parser import *


def test_integer():
    integer = parse('-123', Integer).value
    assert type(integer) is int
    assert integer == -123

def test_string():
    string = parse('"teststring"', String).value
    assert type(string) is str
    assert string == 'teststring'

    assert parse('"test  string"', String).value == 'test  string'
    assert parse("'test  string'", String).value == 'test  string'

def test_identifier():
    parse('abc', Identifier)
    parse('abc2', Identifier)
    parse('Abc', Identifier)
    parse('AbcAbc', Identifier)
    with pytest.raises(SyntaxError):
        parse('1abc', Identifier)
    with pytest.raises(SyntaxError):
        parse('abc.abc', Identifier)

def test_field():
    field = parse('abc', Field)
    assert field.name == 'abc'
    assert field.model is None
    field = parse('Model.abc', Field)
    assert field.model == 'Model'
    assert field.name == 'abc'

def test_aggregator():
    assert parse('SUM:', Aggregator).type is SumAggregator
    assert parse('AVG:', Aggregator).type is AvgAggregator
    assert parse('COUNT:', Aggregator).type is CountAggregator
    assert parse('MIN:', Aggregator).type is MinAggregator
    assert parse('MAX:', Aggregator).type is MaxAggregator
    with pytest.raises(SyntaxError):
        parse('SUM', Aggregator)
    with pytest.raises(SyntaxError):
        parse('ABC:', Aggregator)

def test_aggregation():
    aggregation = parse('SUM: model.field', Aggregation)
    assert aggregation.aggregator is SumAggregator
    assert type(aggregation.field) is Field
    assert aggregation.field.model == 'model'
    assert aggregation.field.name == 'field'

def test_comparator():
    assert parse('==', Comparator).type is EqComparator
    assert parse('<=', Comparator).type is LeqComparator
    assert parse('>=', Comparator).type is GeqComparator
    assert parse('<', Comparator).type is LessComparator
    assert parse('>', Comparator).type is GreaterComparator
    assert parse('!=', Comparator).type is NeqComparator

def test_comparision():
    parse('abc == abc', Comparision)
    parse('abc <= "test string"', Comparision)
    parse('abc != 1', Comparision)
    parse('\'test string\' > abc', Comparision)
    parse('12 < abc', Comparision)

    comparision = parse('model.abc != "test_string"', Comparision)
    assert comparision.comparator is NeqComparator
    assert comparision.first.model == 'model'
    assert comparision.first.name == 'abc'
    assert comparision.second.value == 'test_string'

def test_logical_operator():
    assert parse('AND', LogicalOperator).type is AndOperator
    assert parse('OR', LogicalOperator).type is OrOperator
    assert parse('XOR', LogicalOperator).type is XorOperator

def test_expression():
    expression = parse('test == abc', Expression)
    assert expression.is_comparision
    assert expression.first.name == 'test'
    assert expression.second.name == 'abc'
    assert expression.comparator is EqComparator

    assert expression.logical_operator is None

    parse('(test == abc) AND (test == test3)', Expression)
    parse('((test == abc) AND (test == test3)) OR (abc <= abc)', Expression)

    expression = parse('(test == "abc abv") AND ((test == 1) OR (abc <= abc))', Expression)
    assert expression.is_logical_expression
    assert expression.first.first.name == 'test'
    assert expression.first.second.value == 'abc abv'
    assert expression.logical_operator is AndOperator

    nested_expression = expression.second
    assert nested_expression.logical_operator is OrOperator
    assert nested_expression.comparator is None

def test_alias():
    alias = parse('ALIAS: test1', Alias)
    assert alias.name == 'test1'
    with pytest.raises(SyntaxError):
        parse('ALIAS: test.test', Alias)

def test_model():
    model = parse('MODEL: model', Model)
    assert model.name == 'model'
    assert model.alias is None

    model = parse('MODEL: model2 ALIAS: model3', Model)
    assert model.name == 'model2'
    assert model.alias == 'model3'

def test_join():
    join = parse('JOINON: model.field ALIAS: abc', Join)
    assert join.model == 'model'
    assert join.field == 'field'
    assert join.alias == 'abc'

    join = parse('JOINON: model.field', Join)
    assert join.alias is None

def test_select():
    select = parse('SELECT: (field1, model.field2, model2.field3, MIN: field4)', Select)
    assert select[0].name == 'field1'
    assert select[0].model is None
    assert select[1].name == 'field2'
    assert select[1].model == 'model'
    assert select[2].name == 'field3'
    assert select[2].model == 'model2'
    assert select[3].aggregator is MinAggregator
    assert select[3].field.name == 'field4'

def test_group_by():
    group_by = parse('GROUPBY: (field1, model.field2)', GroupBy)
    assert group_by[0].name == 'field1'
    assert group_by[0].model is None
    assert group_by[1].name == 'field2'
    assert group_by[1].model == 'model'

    with pytest.raises(SyntaxError):
        parse('GROUPBY: (field1, SUM: field2)', GroupBy)

def test_order_by():
    group_by = parse('ORDERBY: (field1, model.field2)', OrderBy)
    assert group_by[0].name == 'field1'
    assert group_by[0].model is None
    assert group_by[1].name == 'field2'
    assert group_by[1].model == 'model'

    with pytest.raises(SyntaxError):
        parse('ORDERBY: (field1, SUM: field2)', OrderBy)

def test_where():
    where = parse('WHERE: abc <= "test"', Where)
    assert where.expression.first.name == 'abc'
    assert where.expression.second.value == 'test'
    parse('WHERE: (abc == 1) AND (abc <= "test")', Where)

def test_query():
    query_str = '''
    MODEL: modelname ALIAS: modelalias1
    JOINON: modelalias1.field ALIAS: modelalias2
    JOINON: modelalias2.field2
    SELECT: (
        abc,
        field2,
        modelalias1.field3,
        SUM: field.field
        )
    GROUPBY: (
        field2.abc2 )
    ORDERBY: (
        field2 )
    WHERE: (abc <= "asfd") AND (abc.field != 2)
    '''

    query = parse(query_str, Query)
    assert query.model.name == 'modelname'
    assert query.model.alias == 'modelalias1'
    assert len(query.joins) == 2
    assert query.joins[0].model == 'modelalias1'
    assert query.joins[0].field == 'field'
    assert query.joins[0].alias == 'modelalias2'
    assert query.joins[1].model == 'modelalias2'
    assert query.joins[1].field == 'field2'
    assert query.joins[1].alias is None
    assert len(query.select) == 4
    assert query.select[0].model is None
    assert query.select[0].name == 'abc'
    assert query.select[1].name == 'field2'
    assert query.select[2].name == 'field3'
    assert query.select[3].aggregator is SumAggregator
    assert query.select[3].field.model == 'field'
    assert query.select[3].field.name == 'field'
    assert len(query.group_by) == 1
    assert query.group_by[0].model == 'field2'
    assert query.group_by[0].name == 'abc2'
    assert len(query.order_by) == 1
    assert query.order_by[0].model is None
    assert query.order_by[0].name == 'field2'
    assert query.where.expression.is_logical_expression
    assert query.where.expression.first.is_comparision

    query_str = '''
        MODEL: modelname ALIAS: modelalias1
        JOINON: modelalias1.field ALIAS: modelalias2
        JOINON: modelalias2.field2
        SELECT: (
            abc,
            field2,
            modelalias1.field3,
            SUM: field.field
            )
        GROUPBY: (
            field2.abc2 )
        WHERE: (abc <= "asfd") AND (abc.field != 2)
        '''

    query = parse(query_str, Query)
    assert query.order_by is None