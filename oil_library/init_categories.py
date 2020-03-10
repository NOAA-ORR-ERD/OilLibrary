'''
    This is where we handle the initialization of the oil categories.

    Basically, we have a number of oil categories arranged in a tree
    structure.  This will make it possible to create an expandable and
    collapsible way for users to find oils by the general 'type' of oil
    they are looking for, starting from very general types and navigating
    to more specific types.

    So we would like each oil to be linked to one or more of these
    categories.  For most of the oils we should be able to do this using
    generalized methods.  But there will very likely be some records
    we just have to link in a hard-coded way.

    The selection criteria for assigning refined products to different
    categories on the oil selection screen, depends upon the API (density)
    and the viscosity at a given temperature, usually at 38 C(100F).
    The criteria follows closely, but not identically, to the ASTM standards
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import logging

import transaction
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from slugify import slugify_filename

import unit_conversion as uc

from .models import Oil, ImportedRecord, Category
from .oil.estimations import OilWithEstimation
from .oil_library_parse import OilLibraryFile

logger = logging.getLogger(__name__)


def process_categories(session, settings):
    logger.info('Purging Categories...')
    num_purged = clear_categories(session)

    logger.info('{0} categories purged.'.format(num_purged))
    logger.info('Orphaned categories: {}'
                .format(session.query(Category).all()))

    logger.info('Loading Categories...')
    load_categories(session)
    logger.info('Finished!!!')

    logger.info('Here are our newly built categories...')
    for c in session.query(Category).filter(Category.parent == None):
        for item in list_categories(c):
            logger.info(item)

    link_oils_to_categories(session, settings)


def clear_categories(session):
    categories = session.query(Category).filter(Category.parent == None)

    rowcount = 0
    for o in categories:
        session.delete(o)
        rowcount += 1

    transaction.commit()
    return rowcount


def load_categories(session):
    crude = Category('Crude')
    refined = Category('Refined')
    other = Category('Other')

    crude.append('Condensate')
    crude.append('Light')
    crude.append('Medium')
    crude.append('Heavy')

    refined.append('Light Products (Fuel Oil 1)')
    refined.append('Gasoline')
    refined.append('Kerosene')

    refined.append('Fuel Oil 2')
    refined.append('Diesel')
    refined.append('Heating Oil')

    refined.append('Intermediate Fuel Oil')

    refined.append('Fuel Oil 6 (HFO)')
    refined.append('Bunker')
    refined.append('Heavy Fuel Oil')
    refined.append('Group V')

    other.append('Other')
    other.append('Generic')

    session.add_all([crude, refined, other])
    transaction.commit()


def list_categories(category, indent=0):
    '''
        This is a recursive method to print out our categories
        showing the nesting with tabbed indentation.
    '''
    yield '{0}{1}'.format(' ' * indent, category.name)
    for c in category.children:
        for y in list_categories(c, indent + 4):
            yield y


def link_oils_to_categories(session, settings):
    # now we try to link the oil records with our categories
    # in some kind of automated fashion
    link_crude_light_oils(session)
    link_crude_medium_oils(session)
    link_crude_heavy_oils(session)

    link_refined_fuel_oil_1(session)
    link_refined_fuel_oil_2(session)
    link_refined_ifo(session)
    link_refined_fuel_oil_6(session)

    link_generic_oils(session)
    link_all_other_oils(session)

    manually_recategorize_oils(session, settings)

    show_uncategorized_oils(session)


def link_crude_light_oils(session):
    # our category
    top, categories = get_categories_by_names(session, 'Crude',
                                              ('Light',))

    oils = get_oils_by_api(session, 'Crude', api_min=31.1)

    count = 0
    for o in oils:
        o.categories.extend(categories)
        count += 1

    logger.info('{0} oils added to {1} -> {2}.'
                .format(count, top.name, [n.name for n in categories]))
    transaction.commit()


def link_crude_medium_oils(session):
    # our category
    top, categories = get_categories_by_names(session, 'Crude',
                                              ('Medium',))

    oils = get_oils_by_api(session, 'Crude',
                           api_min=22.3, api_max=31.1)

    count = 0
    for o in oils:
        o.categories.extend(categories)
        count += 1

    logger.info('{0} oils added to {1} -> {2}.'
                .format(count, top.name, [n.name for n in categories]))
    transaction.commit()


def link_crude_heavy_oils(session):
    top, categories = get_categories_by_names(session, 'Crude',
                                              ('Heavy',))

    oils = get_oils_by_api(session, 'Crude', api_max=22.3)

    count = 0
    for o in oils:
        o.categories.extend(categories)
        count += 1

    logger.info('{0} oils added to {1} -> {2}.'
                .format(count, top.name, [n.name for n in categories]))
    transaction.commit()


def link_refined_light_products(session):
    '''
       Category Name:
       - Light Products
       Parent:
       - Refined
       Sample Oils:
       - Cooper Basin Light Naphtha
       - kerosene
       - JP-4
       - avgas
       Density Criteria:
       - API >= 35
       Kinematic Viscosity Criteria:
       - v > 0.0 cSt @ 38 degrees Celcius
    '''
    raise NotImplementedError


def link_refined_fuel_oil_1(session):
    '''
       Category Name:
       - Fuel oil #1/gasoline/kerosene
       Sample Oils:
       - gasoline
       - kerosene
       - JP-4
       - avgas
       Density Criteria:
       - API >= 35
       Kinematic Viscosity Criteria:
       - v <= 2.5 cSt @ 38 degrees Celcius
    '''
    top, categories = get_categories_by_names(session, 'Refined',
                                              ('Light Products (Fuel Oil 1)',
                                               'Gasoline',
                                               'Kerosene'))

    oils = get_oils_by_api(session, 'Refined', api_min=35.0)

    category_temp = 273.15 + 38

    count = 0
    for o in oils:
        o_estim = OilWithEstimation(o)
        viscosity = uc.convert('Kinematic Viscosity', 'm^2/s', 'cSt',
                               o_estim.kvis_at_temp(category_temp))

        if viscosity <= 2.5:
            o.categories.extend(categories)
            count += 1

    logger.info('{0} oils added to {1} -> {2}.'
                .format(count, top.name, [n.name for n in categories]))
    transaction.commit()


def link_refined_fuel_oil_2(session):
    '''
       Category Name:
       - Fuel oil #2/Diesel/Heating Oil
       Sample Oils:
       - Diesel
       - Heating Oil
       - No. 2 Distillate
       Density Criteria:
       - 30 <= API < 39
       Kinematic Viscosity Criteria:
       - 2.5 < v <= 4.0 cSt @ 38 degrees Celcius
    '''
    top, categories = get_categories_by_names(session, 'Refined',
                                              ('Fuel Oil 2',
                                               'Diesel',
                                               'Heating Oil'))

    oils = get_oils_by_api(session, 'Refined',
                           api_min=30.0, api_max=39.0)

    count = 0
    category_temp = 273.15 + 38
    for o in oils:
        o_estim = OilWithEstimation(o)
        viscosity = uc.convert('Kinematic Viscosity', 'm^2/s', 'cSt',
                               o_estim.kvis_at_temp(category_temp))

        if viscosity > 2.5 or viscosity <= 4.0:
            o.categories.extend(categories)
            count += 1

    logger.info('{0} oils added to {1} -> {2}.'
                .format(count, top.name, [n.name for n in categories]))
    transaction.commit()


def link_refined_ifo(session):
    '''
       Category Name:
       - Intermediate Fuel Oil
       Sample Oils:
       - IFO 180
       - Fuel Oil #4
       - Marine Diesel
       Density Criteria:
       - 15 <= API < 30
       Kinematic Viscosity Criteria:
       - 4.0 < v < 200.0 cSt @ 38 degrees Celcius
    '''
    top, categories = get_categories_by_names(session, 'Refined',
                                              ('Intermediate Fuel Oil',))

    oils = get_oils_by_api(session, 'Refined',
                           api_min=15.0, api_max=30.0)

    count = 0
    category_temp = 273.15 + 38
    for o in oils:
        o_estim = OilWithEstimation(o)
        viscosity = uc.convert('Kinematic Viscosity', 'm^2/s', 'cSt',
                               o_estim.kvis_at_temp(category_temp))

        if viscosity > 4.0 or viscosity < 200.0:
            o.categories.extend(categories)
            count += 1

    logger.info('{0} oils added to {1} -> {2}.'
                .format(count, top.name, [n.name for n in categories]))
    transaction.commit()


def link_refined_fuel_oil_6(session):
    '''
       Category Name:
       - Fuel Oil #6/Bunker/Heavy Fuel Oil/Group V
       Sample Oils:
       - Bunker C
       - Residual Oil
       Density Criteria:
       - API < 15
       Kinematic Viscosity Criteria:
       - 200.0 <= v cSt @ 50 degrees Celcius
    '''
    top, categories = get_categories_by_names(session, 'Refined',
                                              ('Fuel Oil 6 (HFO)',
                                               'Bunker',
                                               'Heavy Fuel Oil',
                                               'Group V'))

    oils = get_oils_by_api(session, 'Refined',
                           api_min=0.0, api_max=15.0)

    count = 0
    category_temp = 273.15 + 50
    for o in oils:
        o_estim = OilWithEstimation(o)
        viscosity = uc.convert('Kinematic Viscosity', 'm^2/s', 'cSt',
                               o_estim.kvis_at_temp(category_temp))

        if viscosity >= 200.0:
            o.categories.extend(categories)
            count += 1

    logger.info('{0} oils added to {1} -> {2}.'
                .format(count, top.name, [n.name for n in categories]))
    transaction.commit()


def link_generic_oils(session):
    '''
        Category Name:
        - Other->Generic
        Criteria:
        - Any oils that have been generically generated.  These are found
          in the OilLibTest data file.  Basically these oils have a name
          that is prefixed with 'GENERIC'.
    '''
    _top, categories = get_categories_by_names(session, 'Other',
                                               ('Generic',))

    if len(categories) == 0:
        logger.warning('Category "Other->Generic" not found!!')
        return

    oils = session.query(Oil).filter(Oil.name.like('GENERIC%')).all()

    count = 0
    for o in oils:
        o.categories.extend(categories)
        count += 1

    logger.info('{0} oils added to {1}.'
                .format(count, [n.name for n in categories]))

    transaction.commit()


def link_all_other_oils(session):
    '''
        Category Name:
        - Other
        Sample Oils:
        - Catalytic Cracked Slurry Oil
        - Fluid Catalytic Cracker Medium Cycle Oil
        Criteria:
        - Any oils that fell outside all the other Category Criteria
    '''
    _top, categories = get_categories_by_names(session, 'Other',
                                               ('Other',))

    oils = (session.query(Oil)
            .filter(Oil.categories == None)
            .all())

    count = 0
    for o in oils:
        o.categories.extend(categories)
        count += 1

    logger.info('{0} oils added to {1}.'
                .format(count, [n.name for n in categories]))
    transaction.commit()


def manually_recategorize_oils(session, settings):
    '''
        When we categorize oils, there is a lot of overlap in their criteria
        that results in oils added to categories when it is fairly clear
        they should not be a part of that category.

        A smaller, but similar, problem is an oil that should be included
        in a category, but its criteria falls outside that of said category
        and it is not added.

        Here we provide a whitelist/blacklist mechanism for manually adding
        and removing oils from categories after the automatic categorization
        processes have completed.
    '''
    fn = settings['blacklist.file']
    fd = OilLibraryFile(fn)
    logger.info('blacklist file version: {}'.format(fd.__version__))

    logger.info('Re-categorizing oils in our blacklist')
    rowcount = 0
    for r in fd.readlines():
        r = [unicode(f, 'utf-8') if f is not None else f
             for f in r]
        recategorize_oil(session, fd.file_columns, r)
        rowcount += 1

    transaction.commit()
    logger.info('Re-categorization finished!!!  {0} rows processed.'
                .format(rowcount))


def recategorize_oil(session, file_columns, row_data):
    file_columns = [slugify_filename(c).lower()
                    for c in file_columns]
    row_dict = dict(zip(file_columns, row_data))

    try:
        oil_obj = (session.query(Oil)
                   .filter(Oil.adios_oil_id == row_dict['adios_oil_id'])
                   .one())
    except Exception:
        logger.error('Re-categorize: could not query oil {}({})'
                     .format(row_dict['oil_name'],
                             row_dict['adios_oil_id']))
        return

    logger.info('Re-categorizing oil: {}'.format(oil_obj.name))

    remove_from_categories(session, oil_obj, row_dict['remove_from'])
    add_to_categories(session, oil_obj, row_dict['add_to'])


def update_oil_in_categories(session, oil_obj, categories, func):
    for c in categories.split(','):
        c = c.strip()
        cat_obj = get_category_by_name(session, c)

        if cat_obj is not None:
            func(oil_obj, cat_obj)
        else:
            logger.error('\t{}("{}", "{}"): Category not accessible'
                         .format(func.__name__, oil_obj.name, c))


def get_category_by_name(session, name):
    '''
        Get the category matching a name.
        - Category name can be a simple name, or a full path to a category
          inside the Category hierarchy.
        - A full path consists of a sequence of category names separated by
          '->' e.g. 'Refined->Gasoline'
    '''
    full_path = name.split('->')
    if len(full_path) > 1:
        # traverse the path
        try:
            cat_obj = (session.query(Category)
                       .filter(Category.name == full_path[0])
                       .filter(Category.parent == None)
                       .one())

            for cat_name in full_path[1:]:
                matching_catlist = [c for c in cat_obj.children
                                    if c.name == cat_name]

                if len(matching_catlist) > 1:
                    raise MultipleResultsFound('One matching child Category '
                                               'required, found {} categories '
                                               'matching the name {}'
                                               .format(len(matching_catlist),
                                                       cat_name))
                elif len(matching_catlist) == 0:
                    raise NoResultFound('child Category matching the name {} '
                                        'not found'
                                        .format(cat_name))

                cat_obj = matching_catlist[0]
        except Exception:
            cat_obj = None
    else:
        # just a simple name
        try:
            cat_obj = (session.query(Category)
                       .filter(Category.name == name).one())
        except Exception:
            cat_obj = None

    return cat_obj


def remove_from_categories(session, oil_obj, categories):
    update_oil_in_categories(session, oil_obj, categories,
                             remove_from_category)


def remove_from_category(oil_obj, category):
    if oil_obj in category.oils:
        logger.debug('\tRemove oil {} from Category {}'
                     .format(oil_obj.name, category.name))
        oil_obj.categories.remove(category)


def add_to_categories(session, oil_obj, categories):
    update_oil_in_categories(session, oil_obj, categories,
                             add_to_category)


def add_to_category(oil_obj, category):
    if oil_obj not in category.oils:
        logger.debug('\tAdd oil {} to Category {}'
                     .format(oil_obj.name, category.name))
        oil_obj.categories.append(category)


def show_uncategorized_oils(session):
    oils = (session.query(Oil)
            .filter(Oil.categories == None)
            .all())

    fd = open('temp.txt', 'w')
    fd.write('adios_oil_id\t'
             'product_type\t'
             'api\t'
             'viscosity\t'
             'pour_point\t'
             'name\n')

    logger.info('{0} oils uncategorized.'.format(len(oils)))

    for o in oils:
        o_estim = OilWithEstimation(o)
        if o.api >= 0:
            if o.api < 15:
                category_temp = 273.15 + 50
            else:
                category_temp = 273.15 + 38

            viscosity = uc.convert('Kinematic Viscosity', 'm^2/s', 'cSt',
                                   o_estim.kvis_at_temp(category_temp))
        else:
            viscosity = None

        fd.write('{0.imported.adios_oil_id}\t'
                 '{0.imported.product_type}\t'
                 '{0.api}\t'
                 '{1}\t'
                 '({0.pour_point_min_k}, {0.pour_point_max_k})\t'
                 '{0.name}\n'
                 .format(o, viscosity))


def get_oils_by_api(session, product_type,
                    api_min=None, api_max=None):
    '''
        After we have performed our Oil estimations, all oils should have a
        valid API value.
    '''
    oil_query = (session.query(Oil).join(ImportedRecord)
                 .filter(ImportedRecord.product_type == product_type))

    if api_max is not None:
        oil_query = oil_query.filter(Oil.api <= api_max)

    if api_min is not None:
        oil_query = oil_query.filter(Oil.api > api_min)

    return oil_query.all()


def get_categories_by_names(session, top_name, child_names):
    '''
        Get the top level category by name, and a list of child categories
        directly underneath it by their names.

        This is a utility function that serves some common functionality in
        our various categorization functions.  Probably not useful outside
        of this module.
    '''
    try:
        top_category = (session.query(Category)
                        .filter(Category.parent == None)
                        .filter(Category.name == top_name)
                        .one())
    except MultipleResultsFound as ex:
        ex.message = ('Multiple top categories named "{}" found.'
                      .format(top_name))
        ex.args = (ex.message, )

        raise ex
    except NoResultFound:
        ex.message = ('Top category "{}" not found.'.format(top_name))
        ex.args = (ex.message, )

        raise ex

    child_categories = [c for c in top_category.children
                        if c.name in child_names]

    return top_category, child_categories
