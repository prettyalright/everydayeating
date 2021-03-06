import datetime

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.forms.models import ModelForm, BaseInlineFormSet, BaseModelFormSet
from django.test import TestCase

from accounts.models import Household, Profile

from food.models import validate_positive, validate_positive_or_zero, Comestible, Ingredient, Dish, Amount, Meal, Portion
from food.views import BaseMealInlineFormSet, DishMultiplyForm, DishDuplicateForm, MealDuplicateForm, get_sum_day_calories, get_avg_week_calories, get_week_starts_in_month


fake_pk = 9999999999


class ValidatorsTestCase(TestCase):
    def test_validate_positive(self):
        validate_positive(1)
        self.assertRaises(ValidationError, validate_positive, 0)
        self.assertRaises(ValidationError, validate_positive, -1)
#        # This would be helpful if there were more than one point in the
#        # function where the exception could be raised, but it's not necessary
#        # here.
#        with self.assertRaises(ValidationError) as context:
#            validate_positive(0)
#            self.assertEqual(context.exception.message, u'Enter a number greater than 0')

    def test_validate_positive_or_zero(self):
        validate_positive_or_zero(1)
        validate_positive_or_zero(0)
        self.assertRaises(ValidationError, validate_positive, -1)


class FoodModelsTestCase(TestCase):
    def test_dish_pretty_cooks(self):
        # Create users, household & dish
        test_user_one = User.objects.create_user('testuser1',
                                                 'test@example.com',
                                                 'testpassword')
        test_user_two = User.objects.create_user('testuser2',
                                                 'test@example.com',
                                                 'testpassword')
        test_user_three = User.objects.create_user('testuser3',
                                                   'test@example.com',
                                                   'testpassword')
        test_user_four = User.objects.create_user('testuser4',
                                                  'test@example.com',
                                                  'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user_one)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 04, 19),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')

        dish.cooks.add(test_user_one)
        self.assertEqual(dish.pretty_cooks(),
                         u'testuser1')

        dish.cooks.add(test_user_two)
        self.assertEqual(dish.pretty_cooks(),
                         u'testuser1 and testuser2')

        dish.cooks.add(test_user_three)
        self.assertEqual(dish.pretty_cooks(),
                         u'testuser1, testuser2 and testuser3')

        dish.cooks.add(test_user_four)
        self.assertEqual(dish.pretty_cooks(),
                         u'testuser1, testuser2, testuser3 and testuser4')


class FoodViewsTestCase(TestCase):
    def test_food_index(self):
        response = self.client.get(reverse('food_index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
#        print response.templates
#        for template in response.templates:
#            print template.name
#        print response.context

    def test_login(self):
        # Create a user first:         (username, email,             password)
        user = User.objects.create_user('jenny', 'jenny@example.com', 'jenny')

        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/login.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Not sure if it's necessary to check these - they are provided by
        # django.contrib.auth.views.login
        self.assertTrue('csrf_token' in response.context)
        self.assertTrue('form' in response.context)
        # user is AnonymousUser here:
        self.assertFalse(response.context['user'].is_authenticated())

        # Try to login with the wrong password
        # If the correct login test comes before this one, this one has an
        # authenticated user in the response, which seems pretty broken...
        response = self.client.post(reverse('login'),
                                    data={'username': 'jenny',
                                          'password': 'wrong'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/login.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # user is still AnonymousUser here:
        self.assertFalse(response.context['user'].is_authenticated())
        self.assertTrue(u"Please enter a correct username and password. Note that both fields are case-sensitive." in
                                response.context['form'].non_field_errors())

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'jenny',
                                          'password': 'jenny'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next' - test again with 'next' set...
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Login correctly, with 'next' set
        response = self.client.post(reverse('login'),
                                    data={'username': 'jenny',
                                          'password': 'jenny',
                                          'next': reverse('ingredient_list')},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # redirects to ingredient_list
        self.assertTemplateUsed(response, 'food/ingredient_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

    def test_logout(self):
        # Create a user first:         (username, email,             password)
        user = User.objects.create_user('jenny', 'jenny@example.com', 'jenny')

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'jenny',
                                          'password': 'jenny'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Logout
        response = self.client.get(reverse('logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # Redirects to food index
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # user is still AnonymousUser here:
        self.assertFalse(response.context['user'].is_authenticated())

################################################################################
# Ingredient views tests

    def test_ingredient_list(self):
        response = self.client.get(reverse('ingredient_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('ingredient_list' in response.context)

    def test_ingredient_add(self):
        # @login_required so can't add an ingredient yet
        response = self.client.get(reverse('ingredient_add'), follow=True)
        self.assertFalse(response.context['user'].is_authenticated())
        # Redirects to login page
        self.assertRedirects(response,
                             u'food/login/?next=/food/ingredients/add/',
                             status_code=302,
                             target_status_code=200,
                             )
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/login.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(response.context['next'], u'/food/ingredients/add/')

        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        self.client.login(username=test_user.username, password='testpassword')

        response = self.client.get(reverse('ingredient_add'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_form.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('form' in response.context)
        # Is this necessary? The form is created by the generic view anyway...
        self.assertIsInstance(response.context['form'], ModelForm)
        self.assertTrue(response.context['user'].is_authenticated())

        # Add a good ingredient
        response = self.client.post(reverse('ingredient_add'),
                                    data={'name': 'Test ingredient good',
                                          'quantity': 100,
                                          'unit': 'g',
                                          'calories': 75},
                                    follow=True)
        # Redirects to ingredient_list
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(Ingredient.objects.count(), 1)
        ingredient = Ingredient.objects.get(name='Test ingredient good')
        # is_dish should be set to False on save (default True)
        self.assertFalse(ingredient.is_dish)

        # Try to add an ingredient with invalid quantity and calories values
        response = self.client.post(reverse('ingredient_add'),
                                    data={'name': 'Test ingredient bad',
                                          # quantity should be positive
                                          'quantity': 0,
                                          'unit': 'g',
                                          'calories': -75})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_form.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a number greater than 0' in
                                response.context['form']['quantity'].errors)
        self.assertTrue(u'Enter a number not less than 0' in
                                response.context['form']['calories'].errors)
        self.assertRaises(ObjectDoesNotExist, Ingredient.objects.get,
                                              name='Test ingredient bad')

    def test_ingredient_detail(self):
        ingredient = Ingredient.objects.create(name = 'Test ingredient',
                                               quantity = 100,
                                               unit = 'g',
                                               calories = 75)
        with self.assertNumQueries(3):
            response = self.client.get(reverse('ingredient_detail',
                                               kwargs={'pk': ingredient.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('ingredient' in response.context)

        # Try to display an ingredient which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Ingredient.objects.get,
                                              pk=fake_pk)
        response = self.client.get(reverse('ingredient_detail',
                                            kwargs={'pk': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_ingredient_edit(self):
        # Create an ingredient
        ingredient = Ingredient.objects.create(name = 'Test ingredient',
                                               quantity = 100,
                                               unit = 'g',
                                               calories = 75)
        # @login_required so can't edit an ingredient yet
        response = self.client.get(reverse('ingredient_edit',
                                           kwargs={'pk': ingredient.id}),
                                           follow=True)
        self.assertFalse(response.context['user'].is_authenticated())
        # Redirects to login page
        self.assertRedirects(response,
                             u'food/login/?next=/food/ingredients/1/edit/',
                             status_code=302,
                             target_status_code=200,
                             )
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/login.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(response.context['next'], u'/food/ingredients/1/edit/')

        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        self.client.login(username=test_user.username, password='testpassword')

        response = self.client.get(reverse('ingredient_edit',
                                           kwargs={'pk': ingredient.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_form.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('ingredient' in response.context)
        self.assertTrue('form' in response.context)
        # Is this necessary? The form is created by the generic view anyway...
        self.assertIsInstance(response.context['form'], ModelForm)
        self.assertTrue(response.context['user'].is_authenticated())

        # Edit an ingredient correctly
        response = self.client.post(reverse('ingredient_edit',
                                            kwargs={'pk': ingredient.id}),
                                    data={'name': 'Test ingredient',
                                          'quantity': 100,
                                          'unit': 'g',
                                          'calories': 5},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # Redirects to ingredient_list
        self.assertTemplateUsed(response, 'food/ingredient_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        edited_ingredient = Ingredient.objects.get(pk=ingredient.id)
        self.assertEqual(edited_ingredient.calories, 5)

        # Try to edit an ingredient with invalid quantity and calories values
        response = self.client.post(reverse('ingredient_edit',
                                            kwargs={'pk': ingredient.id}),
                                    data={# quantity should be positive
                                          'quantity': 0,
                                          # calories should be positive or zero
                                          'calories': -75},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_form.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a number greater than 0' in
                                response.context['form']['quantity'].errors)
        self.assertTrue(u'Enter a number not less than 0' in
                                response.context['form']['calories'].errors)
        # Check that the ingredient still has its initial values
        edited_ingredient = Ingredient.objects.get(pk=ingredient.id)
        self.assertEqual(edited_ingredient.quantity, 100)
        self.assertEqual(edited_ingredient.calories, 5)

        # Try to edit an ingredient which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Ingredient.objects.get,
                                              pk=fake_pk)
        response = self.client.get(reverse('ingredient_edit',
                                           kwargs={'pk': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_ingredient_delete(self):
        # Create an ingredient
        ingredient = Ingredient.objects.create(name = 'Test ingredient',
                                               quantity = 100,
                                               unit = 'g',
                                               calories = 75)
        # @login_required so can't delete an ingredient yet
        response = self.client.get(reverse('ingredient_delete',
                                           kwargs={'pk': ingredient.id}),
                                           follow=True)
        self.assertFalse(response.context['user'].is_authenticated())
        # Redirects to login page
        self.assertRedirects(response,
                             u'food/login/?next=/food/ingredients/1/delete/',
                             status_code=302,
                             target_status_code=200,
                             )
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/login.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(response.context['next'], u'/food/ingredients/1/delete/')

        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        self.client.login(username=test_user.username, password='testpassword')

        response = self.client.get(reverse('ingredient_delete',
                                           kwargs={'pk': ingredient.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_confirm_delete.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('ingredient' in response.context)
        self.assertTrue(response.context['user'].is_authenticated())

        # Delete an ingredient
        response = self.client.post(reverse('ingredient_delete',
                                            kwargs={'pk': ingredient.id}),
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # Redirects to ingredient_list
        self.assertTemplateUsed(response, 'food/ingredient_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(Ingredient.objects.count(), 0)
        self.assertRaises(ObjectDoesNotExist, Ingredient.objects.get,
                                              pk=ingredient.id)

        # Try to delete an ingredient which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Ingredient.objects.get,
                                              pk=fake_pk)
        response = self.client.get(reverse('ingredient_delete',
                                           kwargs={'pk': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_ingredient_manage(self):
        # Create a user first:         (username, email,             password)
        user = User.objects.create_user('jenny', 'jenny@example.com', 'jenny')

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'jenny',
                                          'password': 'jenny'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Create some ingredients
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)

        response = self.client.get(reverse('ingredient_manage'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_manage.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('formset' in response.context)
        # Is this necessary?
        self.assertIsInstance(response.context['formset'], BaseModelFormSet )
        # Check that it's using RequestContext
        self.assertTrue('csrf_token' in response.context)

        # Edit an ingredient and add a new one correctly
        response = self.client.post(reverse('ingredient_manage'),
                                    data={'form-TOTAL_FORMS': 5,
                                          'form-INITIAL_FORMS': 2,
                                          'form-0-comestible_ptr': ingredient_one.id,
                                          'form-0-name': 'Test ingredient 1',
                                          'form-0-quantity': 100,
                                          'form-0-unit': 'g',
                                          'form-0-calories': 5, # was 75
                                          'form-1-comestible_ptr': ingredient_two.id,
                                          'form-1-name': 'Test ingredient 2',
                                          'form-1-quantity': 100,
                                          'form-1-unit': 'ml',
                                          'form-1-calories': 828,
                                          # new ingredient
                                          'form-2-name': 'Test ingredient 3',
                                          'form-2-quantity': 100,
                                          'form-2-unit': 'g',
                                          'form-2-calories': 80,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'form-3-quantity': 100,
                                          'form-3-unit': 'g',
                                          'form-4-quantity': 100,
                                          'form-4-unit': 'g',
                                          'form-5-quantity': 100,
                                          'form-5-unit': 'g'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # Redirects to ingredient_list
        self.assertTemplateUsed(response, 'food/ingredient_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(Ingredient.objects.count(), 3)
        edited_ingredient_one = Ingredient.objects.get(pk=ingredient_one.id)
        ingredient_three = Ingredient.objects.get(name='Test ingredient 3')
        self.assertEqual(edited_ingredient_one.calories, 5)
        self.assertEqual(ingredient_three.calories, 80)

        # Create an amount and a portion of an ingredient and check that they are
        # updated when the ingredient is edited
        # Get ingredient, to get its current values
        ingredient_one = Ingredient.objects.get(pk=edited_ingredient_one.id)
        # (containing_dish and containing_meal are only created because the
        # amount and portion need values for them)
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        containing_dish = Dish.objects.create(name = "Containing dish",
                                              quantity = 500,
                                              date_cooked = datetime.date(2012, 01, 18),
                                              household = test_household,
                                              recipe_url = u'http://www.example.com/recipeurl/',
                                              unit = 'g')
        containing_dish.cooks.add(test_user)
        containing_meal = Meal.objects.create(name = 'breakfast',
                                              date = datetime.date(2011, 01, 01),
                                              time = datetime.time(7, 30),
                                              household = test_household,
                                              user = test_user)
        amount = Amount.objects.create(contained_comestible = ingredient_one.comestible,
                                       containing_dish = containing_dish,
                                       quantity = 200)
        portion = Portion.objects.create(comestible = ingredient_one.comestible,
                                         meal = containing_meal,
                                         quantity = 300)
        self.assertEqual(ingredient_one.calories, 5)
        self.assertEqual(amount.calories, 10)
        self.assertEqual(portion.calories, 15)

        response = self.client.post(reverse('ingredient_manage'),
                                    data={'form-TOTAL_FORMS': 6,
                                          'form-INITIAL_FORMS': 3,
                                          'form-0-comestible_ptr': ingredient_one.id,
                                          'form-0-name': 'Test ingredient 1',
                                          'form-0-quantity': 100,
                                          'form-0-unit': 'g',
                                          'form-0-calories': 10, # was 5
                                          'form-1-comestible_ptr': ingredient_two.id,
                                          'form-1-name': 'Test ingredient 2',
                                          'form-1-quantity': 100,
                                          'form-1-unit': 'ml',
                                          'form-1-calories': 828,
                                          'form-2-comestible_ptr': ingredient_three.id,
                                          'form-2-name': 'Test ingredient 3',
                                          'form-2-quantity': 100,
                                          'form-2-unit': 'g',
                                          'form-2-calories': 80,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'form-3-quantity': 100,
                                          'form-3-unit': 'g',
                                          'form-4-quantity': 100,
                                          'form-4-unit': 'g',
                                          'form-5-quantity': 100,
                                          'form-5-unit': 'g'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # Redirects to ingredient_list
        self.assertTemplateUsed(response, 'food/ingredient_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        edited_ingredient_one = Ingredient.objects.get(pk=ingredient_one.id)
        updated_amount = Amount.objects.get(pk=amount.id)
        updated_portion = Portion.objects.get(pk=portion.id)
        self.assertEqual(edited_ingredient_one.calories, 10)
        self.assertEqual(updated_amount.calories, 20)
        self.assertEqual(updated_portion.calories, 30)

        # Try to edit an ingredient with invalid quantity and calories values
        response = self.client.post(reverse('ingredient_manage'),
                                    data={'form-TOTAL_FORMS': 6,
                                          'form-INITIAL_FORMS': 3,
                                          'form-0-comestible_ptr': ingredient_one.id,
                                          'form-0-name': 'Test ingredient 1',
                                          # quantity should be positive
                                          'form-0-quantity': 0, # was 100
                                          'form-0-unit': 'g',
                                          # calories should be positive or zero
                                          'form-0-calories': -75, # was 10
                                          'form-1-comestible_ptr': ingredient_two.id,
                                          'form-1-name': 'Test ingredient 2',
                                          'form-1-quantity': 100,
                                          'form-1-unit': 'ml',
                                          'form-1-calories': 828,
                                          'form-2-comestible_ptr': ingredient_three.id,
                                          'form-2-name': 'Test ingredient 3',
                                          'form-2-quantity': 100,
                                          'form-2-unit': 'g',
                                          'form-2-calories': 80,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'form-3-quantity': 100,
                                          'form-3-unit': 'g',
                                          'form-4-quantity': 100,
                                          'form-4-unit': 'g',
                                          'form-5-quantity': 100,
                                          'form-5-unit': 'g'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_manage.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a number greater than 0' in
                                response.context['formset'][0]['quantity'].errors)
        self.assertTrue(u'Enter a number not less than 0' in
                                response.context['formset'][0]['calories'].errors)
        # Check that the ingredient still has its initial values
        edited_ingredient_one = Ingredient.objects.get(pk=ingredient_one.id)
        self.assertEqual(edited_ingredient_one.quantity, 100)
        self.assertEqual(edited_ingredient_one.calories, 10)

        # Try to send a comestible_ptr which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Ingredient.objects.get,
                                              pk=fake_pk)
        self.assertRaises(ObjectDoesNotExist, Comestible.objects.get,
                                              pk=fake_pk)
        response = self.client.post(reverse('ingredient_manage'),
                                    data={'form-TOTAL_FORMS': 6,
                                          'form-INITIAL_FORMS': 3,
                                          'form-0-comestible_ptr': ingredient_one.id,
                                          'form-0-name': 'Test ingredient 1',
                                          'form-0-quantity': 100,
                                          'form-0-unit': 'g',
                                          'form-0-calories': 10,
                                          'form-1-comestible_ptr': fake_pk,
                                          'form-1-name': 'Test ingredient 2',
                                          'form-1-quantity': 100,
                                          'form-1-unit': 'ml',
                                          'form-1-calories': 828,
                                          'form-2-comestible_ptr': ingredient_three.id,
                                          'form-2-name': 'Test ingredient 3',
                                          'form-2-quantity': 100,
                                          'form-2-unit': 'g',
                                          'form-2-calories': 80,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'form-3-quantity': 100,
                                          'form-3-unit': 'g',
                                          'form-4-quantity': 100,
                                          'form-4-unit': 'g',
                                          'form-5-quantity': 100,
                                          'form-5-unit': 'g'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/ingredient_manage.html')
        self.assertTemplateUsed(response, 'food/base.html')
        expected_error = u'Select a valid choice. That choice is not one of the available choices.'
        self.assertTrue(expected_error in
                            response.context['formset'][1]['comestible_ptr'].errors)

################################################################################
# Dish views tests

    def test_dish_list(self):
        response = self.client.get(reverse('dish_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('dish_list' in response.context)

    def test_dish_detail(self):
        # Create a user, household, ingredients, dish & amounts
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        dish.amount_set.create(contained_comestible = ingredient_one,
                               quantity = 50)
        dish.amount_set.create(contained_comestible = ingredient_two,
                               quantity = 150)

        with self.assertNumQueries(6):
            response = self.client.get(reverse('dish_detail',
                                           kwargs={'pk': dish.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('dish' in response.context)
        self.assertTrue('comestibles_in_dish' in response.context)
        self.assertTrue('portions_of_dish' in response.context)
        self.assertTrue('amounts_of_dish' in response.context)

        # Try to display a dish which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Dish.objects.get, pk=fake_pk)
        response = self.client.get(reverse('dish_detail',
                                           kwargs={'pk': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_dish_delete(self):
        # Create a user, household, ingredients, dish & amounts
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        dish.amount_set.create(contained_comestible = ingredient_one,
                               quantity = 50)
        dish.amount_set.create(contained_comestible = ingredient_two,
                               quantity = 150)

        # @login_required so can't delete an ingredient yet
        response = self.client.get(reverse('dish_delete',
                                           kwargs={'pk': dish.id}),
                                           follow=True)
        self.assertFalse(response.context['user'].is_authenticated())
        # Redirects to login page
        self.assertRedirects(response,
                             u'food/login/?next=/food/dishes/3/delete/',
                             status_code=302,
                             target_status_code=200,
                             )
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/login.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(response.context['next'], u'/food/dishes/3/delete/')

        login = self.client.login(username=test_user.username, password='testpassword')

        response = self.client.get(reverse('dish_delete',
                                           kwargs={'pk': dish.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_confirm_delete.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('dish' in response.context)
        self.assertTrue(response.context['user'].is_authenticated())

        # Delete a dish (and its amounts via cascade)
        response = self.client.post(reverse('dish_delete',
                                            kwargs={'pk': dish.id}),
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # Redirects to dish_list
        self.assertTemplateUsed(response, 'food/dish_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(Dish.objects.count(), 0)
        self.assertEqual(Amount.objects.count(), 0)
        self.assertRaises(ObjectDoesNotExist, Dish.objects.get,
                                              pk=dish.id)
        self.assertRaises(ObjectDoesNotExist, Amount.objects.get,
                                              containing_dish=dish.id)

        # Try to delete a dish which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Dish.objects.get, pk=fake_pk)
        response = self.client.get(reverse('dish_delete',
                                           kwargs={'pk': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_dish_add(self):
        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        # Create a household
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'testuser',
                                          'password': 'testpassword'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Create some ingredients
        # Use setUp for this instead of fixtures? FIXME
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)

        response = self.client.get(reverse('dish_add'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('csrf_token' in response.context)
        self.assertTrue('form' in response.context)
        self.assertTrue('formset' in response.context)
        # Is this necessary?
        self.assertIsInstance(response.context['form'], ModelForm)
        self.assertIsInstance(response.context['formset'], BaseInlineFormSet)

        # Add a good dish with an amount
        response = self.client.post(reverse('dish_add'),
                                    data={'name': 'Test dish',
                                          'quantity': 500,
                                          'date_cooked': datetime.date(2012, 01, 18),
                                          'household': test_household.id,
                                          'recipe_url': u'http://www.example.com/recipeurl/',
                                          'cooks': test_user.id,
                                          'unit': 'g',
                                          'amount_set-TOTAL_FORMS': 6,
                                          'amount_set-INITIAL_FORMS': 0,
                                          'amount_set-0-contained_comestible': 1,
                                          'amount_set-0-quantity': 50,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'amount_set-1-quantity': 0,
                                          'amount_set-2-quantity': 0,
                                          'amount_set-3-quantity': 0,
                                          'amount_set-4-quantity': 0,
                                          'amount_set-5-quantity': 0},
                                    follow=True)
        # Redirects to dish_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check dish & amounts created correctly
        self.assertEqual(Dish.objects.count(), 1)
        self.assertEqual(Amount.objects.count(), 1)
        dish = Dish.objects.get(name='Test dish')
        amount_one = Amount.objects.get(pk=1)
        self.assertEqual(dish.quantity, 500)
        self.assertEqual(dish.unit, 'g')
        self.assertEqual(amount_one.quantity, 50)

        # Try to add a dish and an amount with invalid quantity values
        response = self.client.post(reverse('dish_add'),
                                    data={'name': 'Test dish bad',
                                          # quantity should be positive
                                          'quantity': 0,
                                          'date_cooked': datetime.date(2012, 01, 18),
                                          'household': test_household.id,
                                          'recipe_url': u'http://www.example.com/recipeurl/',
                                          'cooks': test_user.id,
                                          'unit': 'g',
                                          'amount_set-TOTAL_FORMS': 6,
                                          'amount_set-INITIAL_FORMS': 0,
                                          'amount_set-0-contained_comestible': 1,
                                          # quantity should be positive
                                          'amount_set-0-quantity': -1,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'amount_set-1-quantity': 0,
                                          'amount_set-2-quantity': 0,
                                          'amount_set-3-quantity': 0,
                                          'amount_set-4-quantity': 0,
                                          'amount_set-5-quantity': 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a number greater than 0' in
                                response.context['form']['quantity'].errors)
        self.assertTrue(u'Enter a number not less than 0' in
                                response.context['formset'][0]['quantity'].errors)
        self.assertEqual(Dish.objects.count(), 1)
        self.assertEqual(Amount.objects.count(), 1)
        self.assertRaises(ObjectDoesNotExist, Dish.objects.get,
                                              name='Test dish bad')

    def test_dish_edit(self):
        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        # Create a household
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'testuser',
                                          'password': 'testpassword'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Create ingredients, dish & amounts
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 100)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 100)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        amount_one = dish.amount_set.create(contained_comestible = ingredient_one,
                                            quantity = 50)
        amount_two = dish.amount_set.create(contained_comestible = ingredient_two,
                                            quantity = 150)

        response = self.client.get(reverse('dish_edit',
                                           kwargs={'dish_id': dish.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('csrf_token' in response.context)
        self.assertTrue('form' in response.context)
        self.assertTrue('formset' in response.context)
        # Is this necessary?
        self.assertIsInstance(response.context['form'], ModelForm)
        self.assertIsInstance(response.context['formset'], BaseInlineFormSet)

        # Edit a dish correctly
        response = self.client.post(reverse('dish_edit',
                                            kwargs={'dish_id': dish.id}),
                                    data={'name': 'Test dish',
                                          'quantity': 400, # was 500
                                          'date_cooked': datetime.date(2012, 01, 18),
                                          'household': test_household.id,
                                          'recipe_url': u'http://www.example.com/recipeurl/',
                                          'cooks': test_user.id,
                                          'unit': 'ml', # was 'g'
                                          'amount_set-TOTAL_FORMS': 8,
                                          'amount_set-INITIAL_FORMS': 2,
                                          # amount id needed here, since a new
                                          # amount is being added to the formset
                                          'amount_set-0-id': amount_one.id,
                                          'amount_set-0-contained_comestible': 1,
                                          'amount_set-0-quantity': 50,
                                          'amount_set-1-id': amount_two.id,
                                          'amount_set-1-contained_comestible': 2,
                                          'amount_set-1-quantity': 180, # was 150
                                          # new amount
                                          'amount_set-2-contained_comestible': 2,
                                          'amount_set-2-quantity': 100,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'amount_set-3-quantity': 0,
                                          'amount_set-4-quantity': 0,
                                          'amount_set-5-quantity': 0,
                                          'amount_set-6-quantity': 0,
                                          'amount_set-7-quantity': 0},
                                    follow=True)
        # Redirects to dish_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check dish & amounts edited/created correctly
        self.assertEqual(Dish.objects.count(), 1)
        self.assertEqual(Amount.objects.count(), 3)
        edited_dish = Dish.objects.get(name='Test dish')
        edited_amount_one = Amount.objects.get(pk=amount_one.id)
        edited_amount_two = Amount.objects.get(pk=amount_two.id)
        amount_three = Amount.objects.get(pk=3)
        self.assertEqual(edited_dish.quantity, 400)
        self.assertEqual(edited_dish.unit, 'ml')
        self.assertEqual(edited_amount_one.quantity, 50)
        self.assertEqual(edited_amount_two.quantity, 180)
        self.assertEqual(amount_three.quantity, 100)

        # Try to edit a dish and an amount with invalid quantity values
        response = self.client.post(reverse('dish_edit',
                                            kwargs={'dish_id': dish.id}),
                                    data={'name': 'Test dish',
                                          # quantity should be positive
                                          'quantity': 0, # was 400
                                          'date_cooked': datetime.date(2012, 01, 18),
                                          'household': test_household.id,
                                          'recipe_url': u'http://www.example.com/recipeurl/',
                                          'cooks': test_user.id,
                                          'unit': 'ml',
                                          'amount_set-TOTAL_FORMS': 9,
                                          'amount_set-INITIAL_FORMS': 3,
                                          # amount id needed here, apparently -
                                          # because 2 amounts have the same
                                          # comestible?
                                          'amount_set-0-id': amount_one.id,
                                          'amount_set-0-contained_comestible': 1,
                                          'amount_set-0-quantity': 50,
                                          'amount_set-1-id': amount_two.id,
                                          'amount_set-1-contained_comestible': 2,
                                          # quantity should be positive
                                          'amount_set-1-quantity': -100, # was 180
                                          'amount_set-2-id': amount_three.id,
                                          'amount_set-2-contained_comestible': 2,
                                          'amount_set-2-quantity': 100,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'amount_set-3-quantity': 0,
                                          'amount_set-4-quantity': 0,
                                          'amount_set-5-quantity': 0,
                                          'amount_set-6-quantity': 0,
                                          'amount_set-7-quantity': 0,
                                          'amount_set-8-quantity': 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a number greater than 0' in
                                response.context['form']['quantity'].errors)
        self.assertTrue(u'Enter a number not less than 0' in
                                response.context['formset'][1]['quantity'].errors)
        # Check that dish & amounts weren't changed
        edited_dish = Dish.objects.get(name='Test dish')
        edited_amount_one = Amount.objects.get(pk=amount_one.id)
        edited_amount_two = Amount.objects.get(pk=amount_two.id)
        edited_amount_three = Amount.objects.get(pk=amount_three.id)
        self.assertEqual(edited_dish.quantity, 400)
        self.assertEqual(edited_amount_one.quantity, 50)
        self.assertEqual(edited_amount_two.quantity, 180)
        self.assertEqual(edited_amount_three.quantity, 100)

        # Try to edit a dish to make it contain itself
        response = self.client.post(reverse('dish_edit',
                                            kwargs={'dish_id': dish.id}),
                                    data={'name': 'Test dish',
                                          'quantity': 400,
                                          'date_cooked': datetime.date(2012, 01, 18),
                                          'household': test_household.id,
                                          'recipe_url': u'http://www.example.com/recipeurl/',
                                          'cooks': test_user.id,
                                          'unit': 'ml',
                                          'amount_set-TOTAL_FORMS': 9,
                                          'amount_set-INITIAL_FORMS': 3,
                                          # amount id needed here, apparently -
                                          # because 2 amounts have the same
                                          # comestible?
                                          'amount_set-0-id': amount_one.id,
                                          'amount_set-0-contained_comestible': 1,
                                          'amount_set-0-quantity': 50,
                                          'amount_set-1-id': amount_two.id,
                                          'amount_set-1-contained_comestible': dish.id, # was 2
                                          'amount_set-1-quantity': 180,
                                          'amount_set-2-id': amount_three.id,
                                          'amount_set-2-contained_comestible': 2,
                                          'amount_set-2-quantity': 75, # was 100
                                          # Leave the default values for these
                                          # fields unchanged
                                          'amount_set-3-quantity': 0,
                                          'amount_set-4-quantity': 0,
                                          'amount_set-5-quantity': 0,
                                          'amount_set-6-quantity': 0,
                                          'amount_set-7-quantity': 0,
                                          'amount_set-8-quantity': 0},
                                    follow=True)
        # This produces no error message at the moment, to allow following
        # correctly edited amounts to be saved; find a way to get around this!
        # (It just redirects to the dish_detail page.)
        # FIXME
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check that dish & amounts weren't changed, except for the correctly
        # edited amount_three
        edited_dish = Dish.objects.get(name='Test dish')
        edited_amount_one = Amount.objects.get(pk=amount_one.id)
        edited_amount_two = Amount.objects.get(pk=amount_two.id)
        edited_amount_three = Amount.objects.get(pk=amount_three.id)
        self.assertEqual(edited_dish.quantity, 400)
        self.assertEqual(edited_amount_one.quantity, 50) # unchanged
        self.assertEqual(edited_amount_two.contained_comestible.id, 2) # unchanged
        self.assertEqual(edited_amount_three.quantity, 75) # updated

        # Try to edit a dish which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Dish.objects.get, pk=fake_pk)
        response = self.client.get(reverse('dish_edit',
                                           kwargs={'dish_id': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

        # Create an amount and a portion of a dish and check that they are
        # updated when the dish is edited
        # Get dish, to get its current values
        dish = Dish.objects.get(pk=dish.id)
        # (containing_dish and containing_meal are only created because the
        # amount and portion need values for them)
        containing_dish = Dish.objects.create(name = "Containing dish",
                                              quantity = 500,
                                              date_cooked = datetime.date(2012, 01, 18),
                                              household = test_household,
                                              recipe_url = u'http://www.example.com/recipeurl/',
                                              unit = 'g')
        containing_dish.cooks.add(test_user)
        containing_meal = Meal.objects.create(name = 'breakfast',
                                              date = datetime.date(2011, 01, 01),
                                              time = datetime.time(7, 30),
                                              household = test_household,
                                              user = test_user)
        amount_of_dish = Amount.objects.create(contained_comestible = dish.comestible,
                                               containing_dish = containing_dish,
                                               quantity = 100)
        portion_of_dish = Portion.objects.create(comestible = dish.comestible,
                                                 meal = containing_meal,
                                                 quantity = 200)
#        print dish.calories
#        print amount_of_dish.calories
#        print portion_of_dish.calories
        self.assertEqual(dish.calories, 305)
        self.assertEqual(amount_of_dish.calories, 76.25)
        self.assertEqual(portion_of_dish.calories, 152.5)
        self.assertEqual(Dish.objects.count(), 2)
        self.assertEqual(Amount.objects.count(), 4)

        response = self.client.post(reverse('dish_edit',
                                            kwargs={'dish_id': dish.id}),
                                    data={'name': 'Test dish',
                                          'quantity': 400,
                                          'date_cooked': datetime.date(2012, 01, 18),
                                          'household': test_household.id,
                                          'recipe_url': u'http://www.example.com/recipeurl/',
                                          'cooks': test_user.id,
                                          'unit': 'ml',
                                          'amount_set-TOTAL_FORMS': 9,
                                          'amount_set-INITIAL_FORMS': 3,
                                          # amount id needed here, since a new
                                          # amount is being added to the formset
                                          'amount_set-0-id': amount_one.id,
                                          'amount_set-0-contained_comestible': 1,
                                          'amount_set-0-quantity': 50,
                                          'amount_set-1-id': amount_two.id,
                                          'amount_set-1-contained_comestible': 2,
                                          'amount_set-1-quantity': 180, # was 150
                                          # Delete this amount
                                          'amount_set-2-id': amount_three.id,
                                          'amount_set-2-contained_comestible': 2,
                                          'amount_set-2-quantity': 100,
                                          'amount_set-2-DELETE': True,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'amount_set-3-quantity': 0,
                                          'amount_set-4-quantity': 0,
                                          'amount_set-5-quantity': 0,
                                          'amount_set-6-quantity': 0,
                                          'amount_set-7-quantity': 0,
                                          'amount_set-8-quantity': 0},
                                    follow=True)
        # Redirects to dish_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check that amount_three was deleted correctly
        self.assertEqual(Dish.objects.count(), 2)
        self.assertEqual(Amount.objects.count(), 3)
        self.assertRaises(ObjectDoesNotExist, Amount.objects.get,
                                              pk=amount_three.id)
        # Check that dish and the amount and portion of it were updated correctly
        updated_dish = Dish.objects.get(pk=dish.id)
        updated_amount_of_dish = Amount.objects.get(pk=amount_of_dish.id)
        updated_portion_of_dish = Portion.objects.get(pk=portion_of_dish.id)
#        print updated_dish.calories
#        print updated_amount_of_dish.calories
#        print updated_portion_of_dish.calories
        self.assertEqual(updated_dish.calories, 230)
        self.assertEqual(updated_amount_of_dish.calories, 57.5)
        self.assertEqual(updated_portion_of_dish.calories, 115)

    def test_dish_multiply(self):
        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        # Create a household
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'testuser',
                                          'password': 'testpassword'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Create ingredients, dish & amounts
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        dish.amount_set.create(contained_comestible = ingredient_one,
                               quantity = 50)
        dish.amount_set.create(contained_comestible = ingredient_two,
                               quantity = 150)

        response = self.client.get(reverse('dish_multiply',
                                           kwargs={'dish_id': dish.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_multiply.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('csrf_token' in response.context)
        self.assertTrue('form' in response.context)
        self.assertIsInstance(response.context['form'], DishMultiplyForm)

        # Multiply a dish correctly
        response = self.client.post(reverse('dish_multiply',
                                            kwargs={'dish_id': dish.id}),
                                    data={'operation': 'multiply',
                                          'factor': 2},
                                    follow=True)
        # Redirects to dish_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check dish & amounts multiplied correctly
        self.assertEqual(Dish.objects.count(), 1)
        self.assertEqual(Amount.objects.count(), 2)
        dish = Dish.objects.get(pk=dish.id)
        amount_one = Amount.objects.get(contained_comestible=ingredient_one)
        amount_two = Amount.objects.get(contained_comestible=ingredient_two)
        self.assertEqual(dish.quantity, 1000)
        self.assertEqual(amount_one.quantity, 100)
        self.assertEqual(amount_two.quantity, 300)

        # Divide a dish correctly
        response = self.client.post(reverse('dish_multiply',
                                            kwargs={'dish_id': dish.id}),
                                    data={'operation': 'divide',
                                          'factor': 2},
                                    follow=True)
        # Redirects to dish_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check dish & amounts divided correctly
        self.assertEqual(Dish.objects.count(), 1)
        self.assertEqual(Amount.objects.count(), 2)
        dish = Dish.objects.get(pk=dish.id)
        amount_one = Amount.objects.get(contained_comestible=ingredient_one)
        amount_two = Amount.objects.get(contained_comestible=ingredient_two)
        self.assertEqual(dish.quantity, 500)
        self.assertEqual(amount_one.quantity, 50)
        self.assertEqual(amount_two.quantity, 150)

        # Try to multiply a dish with an invalid factor value
        response = self.client.post(reverse('dish_multiply',
                                            kwargs={'dish_id': dish.id}),
                                    data={'operation': 'multiply',
                                          # factor should be positive
                                          'factor': -2},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_multiply.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a number greater than 0' in
                                response.context['form']['factor'].errors)

        # Try to multiply a dish which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Dish.objects.get, pk=fake_pk)
        response = self.client.get(reverse('dish_multiply',
                                           kwargs={'dish_id': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_dish_duplicate(self):
        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        # Create a household
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'testuser',
                                          'password': 'testpassword'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Create ingredients, dish & amounts
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)
        old_dish = Dish.objects.create(name = 'Test dish',
                                       quantity = 500,
                                       date_cooked = datetime.date(2011, 11, 28),
                                       household = test_household,
                                       recipe_url = u'http://www.example.com/recipeurl/',
                                       unit = 'g')
        old_dish.cooks.add(test_user)
        old_dish.amount_set.create(contained_comestible = ingredient_one,
                                   quantity = 50)
        old_dish.amount_set.create(contained_comestible = ingredient_two,
                                   quantity = 150)

        response = self.client.get(reverse('dish_duplicate',
                                           kwargs={'dish_id': old_dish.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_duplicate.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('csrf_token' in response.context)
        self.assertTrue('form' in response.context)
        self.assertIsInstance(response.context['form'], DishDuplicateForm)

        # Duplicate a dish correctly
        response = self.client.post(reverse('dish_duplicate',
                                            kwargs={'dish_id': old_dish.id}),
                                    data={'date': datetime.date(2011, 11, 30)},
                                    follow=True)
        # Redirects to dish_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check dish & amounts duplicated correctly
        self.assertEqual(Dish.objects.count(), 2)
        self.assertEqual(Amount.objects.count(), 4)
        new_dish = Dish.objects.get(pk=response.context['dish'].id)
        amount_one = Amount.objects.get(contained_comestible=ingredient_one,
                                        containing_dish=new_dish)
        amount_two = Amount.objects.get(contained_comestible=ingredient_two,
                                        containing_dish=new_dish)
        self.assertEqual(new_dish.date_cooked, datetime.date(2011, 11, 30))
        self.assertEqual(new_dish.name, 'Test dish')
        self.assertEqual(new_dish.quantity, 500)
        # Dish.clone() doesn't deal with cooks yet because it's ManyToMany;
        # this needs to be dealt with at some point... FIXME
        self.assertFalse(new_dish.cooks.all())
        self.assertEqual(amount_one.quantity, 50)
        self.assertEqual(amount_two.quantity, 150)

        # Try to duplicate a dish using an invalid date value
        # Is this necessary?
        # The date needs to be sent as a string because datetime won't allow an
        # invalid date (e.g. datetime.date(2011, 11, 50).
        response = self.client.post(reverse('dish_duplicate',
                                            kwargs={'dish_id': old_dish.id}),
                                    data={'date': '50/11/2011'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/dish_duplicate.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a valid date.' in
                                response.context['form']['date'].errors)
        self.assertEqual(Dish.objects.count(), 2)
        self.assertEqual(Amount.objects.count(), 4)

        # Try to duplicate a dish which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Dish.objects.get, pk=fake_pk)
        response = self.client.get(reverse('dish_duplicate',
                                           kwargs={'dish_id': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')


################################################################################
# Meal views tests

    def test_meal_archive(self):
        # 404 if there aren't any meals at all
        self.assertFalse(Meal.objects.all()) # no meals yet
        response = self.client.get(reverse('meal_archive'))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.templates), 1)
        self.assertTemplateUsed(response, '404.html')

        # Create a user, household and meal (without portions)
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        meal = Meal.objects.create(name = 'breakfast',
                                   date = datetime.date(2011, 01, 01),
                                   time = datetime.time(7, 30),
                                   household = test_household,
                                   user = test_user)

        response = self.client.get(reverse('meal_archive'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_archive.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('date_list' in response.context)
        self.assertTrue('latest' in response.context)

    def test_meal_archive_year(self):
        # 404 if there aren't any meals in the given year
        self.assertFalse(Meal.objects.filter(date__year=2011)) # no meals in this year
        response = self.client.get(reverse('meal_archive_year',
                                           kwargs={'year': 2011}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.templates), 1)
        self.assertTemplateUsed(response, '404.html')

        # Create a user, household and meal (without portions)
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        meal = Meal.objects.create(name = 'breakfast',
                                   date = datetime.date(2011, 01, 01),
                                   time = datetime.time(7, 30),
                                   household = test_household,
                                   user = test_user)

        response = self.client.get(reverse('meal_archive_year',
                                           kwargs={'year': 2011}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_archive_year.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('year' in response.context)
        self.assertTrue('date_list' in response.context)
        self.assertTrue('meal_list' in response.context)

    def test_meal_archive_month(self):
        # 404 if there aren't any meals in the given month
        self.assertFalse(Meal.objects.filter(date__year=2011, date__month=1)) # no meals in this month
        response = self.client.get(reverse('meal_archive_month',
                                           kwargs={'year': 2011,
                                                   # month needs leading zero
                                                   'month': '01'}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.templates), 1)
        self.assertTemplateUsed(response, '404.html')

        # Create a user, household and meals (without portions)
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        meal = Meal.objects.create(name = 'breakfast',
                                   date = datetime.date(2011, 01, 01),
                                   time = datetime.time(7, 30),
                                   household = test_household,
                                   user = test_user,
                                   # Set calories here to test get_avg_week_calories
                                   calories = 1000)
        # These are 2 months before/after, to check that it really is finding
        # the previous/next months containing a meal
        previous_month_meal = Meal.objects.create(name = 'breakfast',
                                                  date = datetime.date(2010, 11, 01),
                                                  time = datetime.time(7, 30),
                                                  household = test_household,
                                                  user = test_user)
        next_month_meal = Meal.objects.create(name = 'breakfast',
                                                  date = datetime.date(2011, 03, 01),
                                                  time = datetime.time(7, 30),
                                                  household = test_household,
                                                  user = test_user)

        response = self.client.get(reverse('meal_archive_month',
                                           kwargs={'year': 2011,
                                                   'month': '01'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_archive_month.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('meal_list' in response.context)
        self.assertTrue('date_list' in response.context)
        self.assertTrue('week_list' in response.context)
        self.assertTrue(response.context['meal_list'])
        self.assertTrue(response.context['date_list'])
        self.assertTrue(response.context['week_list'])
        week_list = [{'date' : datetime.date(2010, 12, 27), 'calories': 1000},
                     {'date' : datetime.date(2011, 01, 03), 'calories': 0},
                     {'date' : datetime.date(2011, 01, 10), 'calories': 0},
                     {'date' : datetime.date(2011, 01, 17), 'calories': 0},
                     {'date' : datetime.date(2011, 01, 24), 'calories': 0},
                     {'date' : datetime.date(2011, 01, 31), 'calories': 0}]
        self.assertEqual(response.context['week_list'], week_list)
        self.assertTrue('previous_month' in response.context)
        self.assertTrue('next_month' in response.context)
        self.assertEqual(datetime.date(2010, 11, 1),
                         response.context['previous_month'])
        self.assertEqual(datetime.date(2011, 03, 01),
                         response.context['next_month'])

    def test_meal_archive_week(self):
        # 404 if there aren't any meals in the given week
        # Can't filter date on week - use a range instead (range includes both dates)
        first_day = datetime.date(2012, 01, 02)
        last_day = datetime.date(2012, 01, 8)
        self.assertFalse(Meal.objects.filter(date__range=(first_day, last_day))) # no meals in this week
        response = self.client.get(reverse('meal_archive_week',
                                           kwargs={'year': 2012,
                                                   # week doesn't need leading zero
                                                   'week': '1'}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.templates), 1)
        self.assertTemplateUsed(response, '404.html')

        # Create a user, household and meals (without portions)
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        meal = Meal.objects.create(name = 'breakfast',
                                   date = datetime.date(2012, 01, 03), # Tuesday
                                   time = datetime.time(7, 30),
                                   household = test_household,
                                   user = test_user,
                                   # Set calories here to test get_avg_week_calories
                                   calories = 1000)

        # Test first without any meals in previous or next weeks
        # (this is tested separately to complete coverage of get_previous/next_week)
        response = self.client.get(reverse('meal_archive_week',
                                           kwargs={'year': 2012,
                                                   'week': '1'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_archive_week.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('meal_list' in response.context)
        self.assertTrue('date_list' in response.context)
        self.assertTrue(response.context['meal_list'])
        self.assertTrue(response.context['date_list'])
        self.assertTrue('avg_week_calories' in response.context)
        self.assertEqual(response.context['avg_week_calories'], 1000)
        self.assertTrue('previous_week' in response.context)
        self.assertTrue('next_week' in response.context)
        self.assertFalse(response.context['previous_week'])
        self.assertFalse(response.context['next_week'])

        # Create meals in other weeks and test again with them
        # These are 2 weeks before/after, to check that it really is finding
        # the previous/next weeks containing a meal
        previous_week_meal = Meal.objects.create(name = 'breakfast',
                                                 # A Sunday:
                                                 date = datetime.date(2011, 12, 25),
                                                 time = datetime.time(7, 30),
                                                 household = test_household,
                                                 user = test_user)
        next_week_meal = Meal.objects.create(name = 'breakfast',
                                             # A Sunday:
                                             date = datetime.date(2012, 01, 22),
                                             time = datetime.time(7, 30),
                                             household = test_household,
                                             user = test_user)

        response = self.client.get(reverse('meal_archive_week',
                                           kwargs={'year': 2012,
                                                   'week': '1'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_archive_week.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('meal_list' in response.context)
        self.assertTrue('date_list' in response.context)
        self.assertTrue(response.context['meal_list'])
        self.assertTrue(response.context['date_list'])
        self.assertTrue('avg_week_calories' in response.context)
        self.assertEqual(response.context['avg_week_calories'], 1000)
        self.assertTrue('previous_week' in response.context)
        self.assertTrue('next_week' in response.context)
        self.assertEqual(datetime.date(2011, 12, 19), # Monday
                         response.context['previous_week'])
        self.assertEqual(datetime.date(2012, 01, 16), # Monday
                         response.context['next_week'])

    def test_meal_archive_day(self):
        # 404 if there aren't any meals on the given day
        self.assertFalse(Meal.objects.filter(date__year=2011,
                                             date__month=1,
                                             date__day=1)) # no meals on this day
        response = self.client.get(reverse('meal_archive_day',
                                           kwargs={'year': 2011,
                                                   # month needs leading zero
                                                   'month': '01',
                                                   # day needs leading zero
                                                   'day': '01'}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.templates), 1)
        self.assertTemplateUsed(response, '404.html')

        # Create a user, household and meals (without portions)
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        meal = Meal.objects.create(name = 'breakfast',
                                   date = datetime.date(2011, 01, 01),
                                   time = datetime.time(7, 30),
                                   household = test_household,
                                   user = test_user,
                                   # Set calories here to test get_sum_day_calories
                                   calories = 1000)
        # These are 2 months before/after, to check that it really is finding
        # the previous/next days containing a meal
        previous_day_meal = Meal.objects.create(name = 'breakfast',
                                                date = datetime.date(2010, 11, 30),
                                                time = datetime.time(7, 30),
                                                household = test_household,
                                                user = test_user)
        next_day_meal = Meal.objects.create(name = 'breakfast',
                                            date = datetime.date(2011, 03, 03),
                                            time = datetime.time(7, 30),
                                            household = test_household,
                                            user = test_user)

        response = self.client.get(reverse('meal_archive_day',
                                           kwargs={'year': 2011,
                                                   'month': '01',
                                                   'day': '01'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_archive_day.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('meal_list' in response.context)
        self.assertTrue('date_list' in response.context)
        self.assertEqual(len(response.context['meal_list']), 1)
        self.assertFalse(response.context['date_list'])
        self.assertTrue('day_calories' in response.context)
        self.assertEqual(response.context['day_calories'], 1000)
        self.assertTrue('day' in response.context)
        self.assertEqual(datetime.date(2011, 01, 01),
                         response.context['day'])
        self.assertTrue('previous_day' in response.context)
        self.assertTrue('next_day' in response.context)
        self.assertEqual(datetime.date(2010, 11, 30),
                         response.context['previous_day'])
        self.assertEqual(datetime.date(2011, 03, 03),
                         response.context['next_day'])
        self.assertTrue('previous_month' in response.context)
        self.assertTrue('next_month' in response.context)
        self.assertEqual(datetime.date(2010, 11, 01),
                         response.context['previous_month'])
        self.assertEqual(datetime.date(2011, 03, 01),
                         response.context['next_month'])

    def test_meal_list(self):
        response = self.client.get(reverse('meal_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_list.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('meal_list' in response.context)

    def test_meal_detail(self):
        # Create a user, household, ingredients, dish & amounts, meal & portions
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        dish.amount_set.create(contained_comestible = ingredient_one,
                               quantity = 50)
        dish.amount_set.create(contained_comestible = ingredient_two,
                               quantity = 150)
        meal = Meal.objects.create(name = 'breakfast',
                                   date = datetime.date(2012, 01, 18),
                                   time = datetime.time(7, 30),
                                   household = test_household,
                                   user = test_user)
        portion = Portion.objects.create(comestible = dish,
                                         meal = meal,
                                         quantity = 300)

        response = self.client.get(reverse('meal_detail',
                                           kwargs={'pk': meal.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('meal' in response.context)

        # Try to display a meal which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Meal.objects.get, pk=fake_pk)
        response = self.client.get(reverse('meal_detail',
                                           kwargs={'pk': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_meal_delete(self):
        # Create a user, household, ingredients, dish & amounts, meals & portions
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        dish.amount_set.create(contained_comestible = ingredient_one,
                               quantity = 50)
        dish.amount_set.create(contained_comestible = ingredient_two,
                               quantity = 150)
        meal = Meal.objects.create(name = 'breakfast',
                                   date = datetime.date(2012, 01, 18),
                                   time = datetime.time(7, 30),
                                   household = test_household,
                                   user = test_user)
        portion = Portion.objects.create(comestible = dish,
                                         meal = meal,
                                         quantity = 300)
        # There needs to be a meal remaining after deleting one, so that the
        # view it redirects to (meal_archive) doesn't go to 404
        extra_meal = Meal.objects.create(name = 'lunch',
                                         date = datetime.date(2012, 01, 18),
                                         time = datetime.time(12, 30),
                                         household = test_household,
                                         user = test_user)
        extra_portion = Portion.objects.create(comestible = dish,
                                               meal = extra_meal,
                                               quantity = 100)

        response = self.client.get(reverse('meal_delete',
                                           kwargs={'pk': meal.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_confirm_delete.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('meal' in response.context)

        # Delete a meal (and its portion(s) via cascade)
        response = self.client.post(reverse('meal_delete',
                                            kwargs={'pk': meal.id}),
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # Redirects to meal_archive
        self.assertTemplateUsed(response, 'food/meal_archive.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 1)
        self.assertRaises(ObjectDoesNotExist, Meal.objects.get, pk=meal.id)
        self.assertRaises(ObjectDoesNotExist, Portion.objects.get, meal=meal.id)

        # Try to delete a meal which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Meal.objects.get, pk=fake_pk)
        response = self.client.get(reverse('meal_delete',
                                           kwargs={'pk': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 1)

    def test_meal_add(self):
        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        # Create a household
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'testuser',
                                          'password': 'testpassword'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Create ingredients, dish & amounts
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 50)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 100)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        dish.amount_set.create(contained_comestible = ingredient_one,
                               quantity = 50)
        dish.amount_set.create(contained_comestible = ingredient_two,
                               quantity = 150)

        response = self.client.get(reverse('meal_add'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('csrf_token' in response.context)
        self.assertTrue('form' in response.context)
        self.assertTrue('formset' in response.context)
        # Is this necessary?
        self.assertIsInstance(response.context['form'], ModelForm)
        self.assertIsInstance(response.context['formset'], BaseMealInlineFormSet)

        # Add a good meal with portions
        response = self.client.post(reverse('meal_add'),
                                    data={'name': 'breakfast',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(7, 30),
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 6,
                                          'portion_set-INITIAL_FORMS': 0,
                                          'portion_set-0-comestible': ingredient_one.id,
                                          'portion_set-0-quantity': 50,
                                          'portion_set-1-comestible': dish.id,
                                          'portion_set-1-quantity': 100,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-2-quantity': 0,
                                          'portion_set-3-quantity': 0,
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0},
                                    follow=True)
        # Redirects to meal_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check meal & portions created correctly
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 2)
        added_meal = Meal.objects.get(name='breakfast')
        added_portion_one = Portion.objects.get(pk=1)
        added_portion_two = Portion.objects.get(pk=2)
        self.assertEqual(added_meal.time, datetime.time(7, 30))
        self.assertEqual(added_portion_one.quantity, 50)
        self.assertEqual(added_portion_two.quantity, 100)
        # Check dish's remaining quantity
        updated_dish = Dish.objects.get(name='Test dish')
        self.assertEqual(updated_dish.get_remaining_quantity(), 400)

        # Try to add a meal and portions with invalid quantity values
        response = self.client.post(reverse('meal_add'),
                                    data={'name': 'lunch',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(12, 30),
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 6,
                                          'portion_set-INITIAL_FORMS': 0,
                                          'portion_set-0-comestible': ingredient_one.id,
                                          # quantity should be positive
                                          'portion_set-0-quantity': -50,
                                          'portion_set-1-comestible': dish.id,
                                          # 100/500 of dish in breakfast
                                          'portion_set-1-quantity': 400,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-2-quantity': 0,
                                          'portion_set-3-quantity': 0,
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0},
                                      # follow=True
                                      )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a number not less than 0' in
                                response.context['formset'][0]['quantity'].errors)
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 2)
        self.assertRaises(ObjectDoesNotExist, Meal.objects.get, name='lunch')
        self.assertRaises(ObjectDoesNotExist, Portion.objects.get, meal__name='lunch')

        # Try to add a meal and a portion of a dish with a quantity greater
        # than the dish's remaining quantity
        response = self.client.post(reverse('meal_add'),
                                    data={'name': 'dinner',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(19, 30),
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 6,
                                          'portion_set-INITIAL_FORMS': 0,
                                          'portion_set-0-comestible': ingredient_one.id,
                                          'portion_set-0-quantity': 50,
                                          'portion_set-1-comestible': dish.id,
                                          # 100/500 of dish in breakfast
                                          'portion_set-1-quantity': 1000,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-2-quantity': 0,
                                          'portion_set-3-quantity': 0,
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0},
                                      # follow=True
                                      )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')

#        print type(response.context['formset'].errors[1])
#        print response.context['formset'].errors[1]
#        print type(response.context['formset'][1].non_field_errors())
#        print response.context['formset'][1].non_field_errors()[0]

        expected_error = u"This portion's quantity is greater than the remaining quantity of the dish (400 g)."
        self.assertTrue(expected_error in
                            response.context['formset'][1].non_field_errors())
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 2)
        self.assertRaises(ObjectDoesNotExist, Meal.objects.get, name='dinner')
        self.assertRaises(ObjectDoesNotExist, Portion.objects.get, meal__name='dinner')

        # Try to add a meal and portions of a dish with a joint quantity (but
        # not individual quantities) greater than the dish's remaining quantity
        response = self.client.post(reverse('meal_add'),
                                    data={'name': 'snack',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(15, 30),
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 6,
                                          'portion_set-INITIAL_FORMS': 0,
                                          # 100/500 of dish in breakfast
                                          'portion_set-0-comestible': dish.id,
                                          'portion_set-0-quantity': 300,
                                          'portion_set-1-comestible': dish.id,
                                          'portion_set-1-quantity': 300,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-2-quantity': 0,
                                          'portion_set-3-quantity': 0,
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0},
                                      # follow=True
                                      )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')

#        print type(response.context['formset'].errors)
#        print response.context['formset'].errors
#        print type(response.context['formset'].non_form_errors())
#        print response.context['formset'].non_form_errors()

        expected_error = u"The remaining quantity of Test dish (2012-01-18) (400 g) is less than the total quantity of it in this meal."
        self.assertTrue(expected_error in
                            response.context['formset'].non_form_errors())
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 2)
        self.assertRaises(ObjectDoesNotExist, Meal.objects.get, name='snack')
        self.assertRaises(ObjectDoesNotExist, Portion.objects.get, meal__name='snack')

    def test_meal_edit(self):
        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        # Create a household
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'testuser',
                                          'password': 'testpassword'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Create ingredients, dish & amounts, meal & portions
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 50)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 30)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        dish.amount_set.create(contained_comestible = ingredient_one,
                               quantity = 50)
        dish.amount_set.create(contained_comestible = ingredient_two,
                               quantity = 150)
        meal = Meal.objects.create(name = 'breakfast',
                                   date = datetime.date(2012, 01, 18),
                                   time = datetime.time(7, 30),
                                   household = test_household,
                                   user = test_user)
        portion_one = Portion.objects.create(comestible = dish,
                                             meal = meal,
                                             quantity = 100)
        portion_two = Portion.objects.create(comestible = dish,
                                             meal = meal,
                                             quantity = 200)

        response = self.client.get(reverse('meal_edit',
                                           kwargs={'meal_id': meal.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('csrf_token' in response.context)
        self.assertTrue('form' in response.context)
        self.assertTrue('formset' in response.context)
        # Is this necessary?
        self.assertIsInstance(response.context['form'], ModelForm)
        self.assertIsInstance(response.context['formset'], BaseMealInlineFormSet)

        # Edit a meal and portions correctly
        response = self.client.post(reverse('meal_edit',
                                            kwargs={'meal_id': meal.id}),
                                    data={'name': 'breakfast',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(8, 30), # was 7:30
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 8,
                                          'portion_set-INITIAL_FORMS': 2,
                                          # portion id needed when new portions
                                          # are added into the formset
                                          'portion_set-0-id': portion_one.id,
                                          'portion_set-0-comestible': dish.id,
                                          'portion_set-0-quantity': 50, # was 100
                                          'portion_set-1-id': portion_two.id,
                                          'portion_set-1-comestible': dish.id,
                                          'portion_set-1-quantity': 100, # was 200
                                          # 2 new portions...
                                          'portion_set-2-comestible': ingredient_one.id,
                                          'portion_set-2-quantity': 150,
                                          # ...this one to be deleted next
                                          'portion_set-3-comestible': ingredient_two.id,
                                          'portion_set-3-quantity': 15,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0,
                                          'portion_set-6-quantity': 0,
                                          'portion_set-7-quantity': 0},
                                    follow=True)
        # Redirects to meal_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check meal & portions edited/created correctly
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 4)
        edited_meal = Meal.objects.get(name='breakfast')
        edited_portion_one = Portion.objects.get(pk=portion_one.id)
        edited_portion_two = Portion.objects.get(pk=portion_two.id)
        portion_three = Portion.objects.get(pk=3)
        portion_four = Portion.objects.get(pk=4)
        self.assertEqual(edited_meal.time, datetime.time(8, 30))
        # edited_meal.calories are useful to have here to compare with next test
        self.assertEqual(edited_meal.calories, 100.5)
        self.assertEqual(edited_portion_one.quantity, 50)
        self.assertEqual(edited_portion_two.quantity, 100)
        self.assertEqual(portion_three.quantity, 150)
        self.assertEqual(portion_four.quantity, 15)
        # Check dish's remaining quantity
        updated_dish = Dish.objects.get(name='Test dish')
        self.assertEqual(updated_dish.get_remaining_quantity(), 350)

        # Delete a portion correctly
        response = self.client.post(reverse('meal_edit',
                                            kwargs={'meal_id': meal.id}),
                                    data={'name': 'breakfast',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(8, 30), # was 7:30
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 10,
                                          'portion_set-INITIAL_FORMS': 4,
                                          # portion id needed when new portions
                                          # are added into the formset
                                          'portion_set-0-id': portion_one.id,
                                          'portion_set-0-comestible': dish.id,
                                          'portion_set-0-quantity': 50, # was 100
                                          'portion_set-1-id': portion_two.id,
                                          'portion_set-1-comestible': dish.id,
                                          'portion_set-1-quantity': 100, # was 200
                                          'portion_set-2-id': portion_three.id,
                                          'portion_set-2-comestible': ingredient_one.id,
                                          'portion_set-2-quantity': 150,
                                          # Delete portion_four
                                          'portion_set-3-id': portion_four.id,
                                          'portion_set-3-comestible': ingredient_two.id,
                                          'portion_set-3-quantity': 15,
                                          'portion_set-3-DELETE': True,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0,
                                          'portion_set-6-quantity': 0,
                                          'portion_set-7-quantity': 0,
                                          'portion_set-8-quantity': 0,
                                          'portion_set-9-quantity': 0},
                                    follow=True)
        # Redirects to meal_detail
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check portion deleted correctly and meal updated
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 3)
        edited_meal = Meal.objects.get(name='breakfast')
        self.assertEqual(edited_meal.calories, 96)
        self.assertRaises(ObjectDoesNotExist, Portion.objects.get,
                                              pk=portion_four.id)
        # Check dish's remaining quantity
        updated_dish = Dish.objects.get(name='Test dish')
        self.assertEqual(updated_dish.get_remaining_quantity(), 350)

        # Try to edit a meal and portions using invalid quantity values
        response = self.client.post(reverse('meal_edit',
                                            kwargs={'meal_id': meal.id}),
                                    data={'name': 'breakfast',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(8, 30),
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 9,
                                          'portion_set-INITIAL_FORMS': 3,
                                          # portion id needed here, apparently -
                                          # because 2 portions have the same meal
                                          # and comestible?
                                          'portion_set-0-id': portion_one.id,
                                          'portion_set-0-comestible': dish.id,
                                          # quantity should be positive
                                          'portion_set-0-quantity': -50,
                                          'portion_set-1-id': portion_two.id,
                                          'portion_set-1-comestible': dish.id,
                                          'portion_set-1-quantity': 100,
                                          'portion_set-2-id': portion_three.id,
                                          'portion_set-2-comestible': ingredient_one.id,
                                          'portion_set-2-quantity': 150,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-3-quantity': 0,
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0,
                                          'portion_set-6-quantity': 0,
                                          'portion_set-7-quantity': 0,
                                          'portion_set-8-quantity': 0},
                                    # follow=True
                                    )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a number not less than 0' in
                                response.context['formset'][0]['quantity'].errors)
        # Check that meal & portions weren't changed
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 3)
        edited_meal = Meal.objects.get(name='breakfast')
        edited_portion_one = Portion.objects.get(pk=portion_one.id)
        edited_portion_two = Portion.objects.get(pk=portion_two.id)
        edited_portion_three = Portion.objects.get(pk=portion_three.id)
        self.assertEqual(edited_meal.time, datetime.time(8, 30))
        self.assertEqual(edited_portion_one.quantity, 50)
        self.assertEqual(edited_portion_two.quantity, 100)
        self.assertEqual(edited_portion_three.quantity, 150)
        # Check that dish's remaining quantity is still the same
        updated_dish = Dish.objects.get(name='Test dish')
        self.assertEqual(updated_dish.get_remaining_quantity(), 350)

        # Try to edit a meal and a portion of a dish using a quantity greater
        # than the dish's remaining quantity
        response = self.client.post(reverse('meal_edit',
                                            kwargs={'meal_id': meal.id}),
                                    data={'name': 'breakfast',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(8, 30),
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 9,
                                          'portion_set-INITIAL_FORMS': 3,
                                          # portion id needed here, apparently -
                                          # because 2 portions have the same meal
                                          # and comestible?
                                          'portion_set-0-id': portion_one.id,
                                          # 150/500 of dish used already
                                          'portion_set-0-comestible': dish.id,
                                          'portion_set-0-quantity': 450, # was 50
                                          'portion_set-1-id': portion_two.id,
                                          'portion_set-1-comestible': dish.id,
                                          'portion_set-1-quantity': 100, # was 100
                                          'portion_set-2-id': portion_three.id,
                                          'portion_set-2-comestible': ingredient_one.id,
                                          'portion_set-2-quantity': 150,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-3-quantity': 0,
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0,
                                          'portion_set-6-quantity': 0,
                                          'portion_set-7-quantity': 0,
                                          'portion_set-8-quantity': 0},
                                      # follow=True
                                      )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')

#        print type(response.context['formset'].errors[0])
#        print response.context['formset'].errors[0]
#        print type(response.context['formset'][0].non_field_errors())
#        print response.context['formset'][0].non_field_errors()

        expected_error = u"This portion's quantity is greater than the remaining quantity of the dish (400 g)."
        self.assertTrue(expected_error in
                            response.context['formset'][0].non_field_errors())
        # Check that meal & portions weren't changed
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 3)
        edited_meal = Meal.objects.get(name='breakfast')
        edited_portion_one = Portion.objects.get(pk=portion_one.id)
        edited_portion_two = Portion.objects.get(pk=portion_two.id)
        edited_portion_three = Portion.objects.get(pk=portion_three.id)
        self.assertEqual(edited_meal.time, datetime.time(8, 30))
        self.assertEqual(edited_portion_one.quantity, 50)
        self.assertEqual(edited_portion_two.quantity, 100)
        self.assertEqual(edited_portion_three.quantity, 150)
        # Check that dish's remaining quantity is still the same
        updated_dish = Dish.objects.get(name='Test dish')
        self.assertEqual(updated_dish.get_remaining_quantity(), 350)

        # Try to edit a meal and portions of a dish using a joint quantity (but
        # not individual quantities) greater than the dish's remaining quantity
        response = self.client.post(reverse('meal_edit',
                                            kwargs={'meal_id': meal.id}),
                                    data={'name': 'breakfast',
                                          'date': datetime.date(2012, 01, 18),
                                          'time': datetime.time(8, 30),
                                          'household': test_household.id,
                                          'user': test_user.id,
                                          'portion_set-TOTAL_FORMS': 9,
                                          'portion_set-INITIAL_FORMS': 3,
                                          # portion id needed here, apparently -
                                          # because 2 portions have the same meal
                                          # and comestible?
                                          'portion_set-0-id': portion_one.id,
                                          # 150/500 of dish used already
                                          'portion_set-0-comestible': dish.id,
                                          'portion_set-0-quantity': 250, # was 50
                                          'portion_set-1-id': portion_two.id,
                                          'portion_set-1-comestible': dish.id,
                                          'portion_set-1-quantity': 300, # was 100
                                          'portion_set-2-id': portion_three.id,
                                          'portion_set-2-comestible': ingredient_one.id,
                                          'portion_set-2-quantity': 150,
                                          # Leave the default values for these
                                          # fields unchanged
                                          'portion_set-3-quantity': 0,
                                          'portion_set-4-quantity': 0,
                                          'portion_set-5-quantity': 0,
                                          'portion_set-6-quantity': 0,
                                          'portion_set-7-quantity': 0,
                                          'portion_set-8-quantity': 0},
                                      # follow=True
                                      )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_edit.html')
        self.assertTemplateUsed(response, 'food/base.html')

#        print type(response.context['formset'].errors)
#        print response.context['formset'].errors
#        print type(response.context['formset'].non_form_errors())
#        print response.context['formset'].non_form_errors()

        expected_error = u"The remaining quantity of Test dish (2012-01-18) (500 g) is less than the total quantity of it in this meal."
        self.assertTrue(expected_error in
                            response.context['formset'].non_form_errors())
        # Check that meal & portions weren't changed
        self.assertEqual(Meal.objects.count(), 1)
        self.assertEqual(Portion.objects.count(), 3)
        edited_meal = Meal.objects.get(name='breakfast')
        edited_portion_one = Portion.objects.get(pk=portion_one.id)
        edited_portion_two = Portion.objects.get(pk=portion_two.id)
        edited_portion_three = Portion.objects.get(pk=portion_three.id)
        self.assertEqual(edited_meal.time, datetime.time(8, 30))
        self.assertEqual(edited_portion_one.quantity, 50)
        self.assertEqual(edited_portion_two.quantity, 100)
        self.assertEqual(edited_portion_three.quantity, 150)
        # Check that dish's remaining quantity is still the same
        updated_dish = Dish.objects.get(name='Test dish')
        self.assertEqual(updated_dish.get_remaining_quantity(), 350)

        # Try to edit a meal which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Meal.objects.get, pk=fake_pk)
        response = self.client.get(reverse('meal_edit',
                                           kwargs={'meal_id': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_meal_duplicate(self):
        # Create a user
        test_user = User.objects.create_user('testuser', # username
                                             'test@example.com', # email
                                             'testpassword') # password
        # Create a household
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)

        # Login correctly
        response = self.client.post(reverse('login'),
                                    data={'username': 'testuser',
                                          'password': 'testpassword'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        # LOGIN_REDIRECT_URL = '/food/' in settings.py is used here, because no
        # value is given for 'next'
        self.assertTemplateUsed(response, 'food/food_index.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(response.context['user'].is_authenticated())

        # Create ingredients, dish & amounts, meal & portions
        ingredient_one = Ingredient.objects.create(name = 'Test ingredient 1',
                                                   quantity = 100,
                                                   unit = 'g',
                                                   calories = 75)
        ingredient_two = Ingredient.objects.create(name = 'Test ingredient 2',
                                                   quantity = 100,
                                                   unit = 'ml',
                                                   calories = 828)
        dish = Dish.objects.create(name = 'Test dish',
                                   quantity = 500,
                                   date_cooked = datetime.date(2012, 01, 18),
                                   household = test_household,
                                   recipe_url = u'http://www.example.com/recipeurl/',
                                   unit = 'g')
        dish.cooks.add(test_user)
        dish.amount_set.create(contained_comestible = ingredient_one,
                               quantity = 50)
        dish.amount_set.create(contained_comestible = ingredient_two,
                               quantity = 150)
        old_meal = Meal.objects.create(name = 'breakfast',
                                       date = datetime.date(2012, 01, 18),
                                       time = datetime.time(7, 30),
                                       household = test_household,
                                       user = test_user)
        old_portion_one = Portion.objects.create(comestible = ingredient_one,
                                                 meal = old_meal,
                                                 quantity = 75)
        old_portion_two = Portion.objects.create(comestible = dish,
                                                 meal = old_meal,
                                                 quantity = 100)

        response = self.client.get(reverse('meal_duplicate',
                                           kwargs={'meal_id': old_meal.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_duplicate.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue('csrf_token' in response.context)
        self.assertTrue('form' in response.context)
        self.assertIsInstance(response.context['form'], MealDuplicateForm)

        # Duplicate a dish correctly
        response = self.client.post(reverse('meal_duplicate',
                                            kwargs={'meal_id': old_meal.id}),
                                    data={'date': datetime.date(2012, 01, 19)},
                                    follow=True)
        # Redirects to meal_detail (for new meal)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_detail.html')
        self.assertTemplateUsed(response, 'food/base.html')
        # Check meal & portions duplicated correctly
        self.assertEqual(Meal.objects.count(), 2)
        self.assertEqual(Portion.objects.count(), 4)
        new_meal = Meal.objects.get(pk=response.context['meal'].id)
        new_portion_one = Portion.objects.get(comestible=ingredient_one,
                                              meal=new_meal)
        new_portion_two = Portion.objects.get(comestible=dish,
                                              meal=new_meal)
        self.assertEqual(new_meal.date, datetime.date(2012, 01, 19))
        self.assertEqual(new_meal.name, 'breakfast')
        self.assertEqual(new_meal.user, test_user)
        self.assertEqual(new_portion_one.quantity, 75)
        # This is a quantity of the original dish; this should be changed to
        # make sure that the dish's remaining quantity isn't exceeded, and if it
        # would be, to ask if the dish should be duplicated (cooked again)
        self.assertEqual(new_portion_two.quantity, 100)

        # Is this necessary?
        # Try to duplicate a meal using an invalid date value
        # The date needs to be sent as a string because datetime won't allow an
        # invalid date (e.g. datetime.date(2011, 11, 50).
        response = self.client.post(reverse('meal_duplicate',
                                            kwargs={'meal_id': old_meal.id}),
                                    data={'date': '50/11/2011'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.templates), 2)
        self.assertTemplateUsed(response, 'food/meal_duplicate.html')
        self.assertTemplateUsed(response, 'food/base.html')
        self.assertTrue(u'Enter a valid date.' in
                                response.context['form']['date'].errors)
        self.assertEqual(Meal.objects.count(), 2)
        self.assertEqual(Portion.objects.count(), 4)

        # Try to duplicate a meal which doesn't exist
        self.assertRaises(ObjectDoesNotExist, Meal.objects.get, pk=fake_pk)
        response = self.client.get(reverse('meal_duplicate',
                                           kwargs={'meal_id': fake_pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')


class DateViewsTestCase(TestCase):
    def test_get_sum_day_calories(self):
        day = datetime.date(2012, 01, 01)
        day_calories = get_sum_day_calories(day)
        # No meals for this date yet, so 0 calories
        self.assertEqual(0, day_calories)
        # Create a user, household and some meals (without portions) for this date
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        Meal.objects.create(name = 'breakfast',
                            date = day,
                            time = datetime.time(7, 30),
                            household = test_household,
                            user = test_user,
                            calories = 500)
        Meal.objects.create(name = 'lunch',
                            date = day,
                            time = datetime.time(12, 30),
                            household = test_household,
                            user = test_user,
                            calories = 650)
        Meal.objects.create(name = 'dinner',
                            date = day,
                            time = datetime.time(19, 30),
                            household = test_household,
                            user = test_user,
                            calories = 850)
        day_calories = get_sum_day_calories(day)
        self.assertEqual(2000, day_calories)
        # test for number of database queries

    def test_get_avg_week_calories(self):
        day = datetime.date(2012, 01, 02) # Monday - must be week start ATM...
        avg_calories = get_avg_week_calories(day)
        # No meals for this week yet, so 0 calories
        self.assertEqual(0, avg_calories)
        # Create a user, household and some meals (without portions) for this
        # date and other days in the same week
        test_user = User.objects.create_user('testuser',
                                             'test@example.com',
                                             'testpassword')
        test_household = Household.objects.create(name = 'Test household',
                                                  admin = test_user)
        Meal.objects.create(name = 'breakfast',
                            date = day,
                            time = datetime.time(7, 30),
                            household = test_household,
                            user = test_user,
                            calories = 500)
        Meal.objects.create(name = 'lunch',
                            date = day,
                            time = datetime.time(12, 30),
                            household = test_household,
                            user = test_user,
                            calories = 650)
        Meal.objects.create(name = 'dinner',
                            date = day,
                            time = datetime.time(19, 30),
                            household = test_household,
                            user = test_user,
                            calories = 850)
        Meal.objects.create(name = 'breakfast',
                            date = day + datetime.timedelta(days=1), # Tuesday
                            time = datetime.time(7, 30),
                            household = test_household,
                            user = test_user,
                            calories = 500)
        Meal.objects.create(name = 'breakfast',
                            date = day + datetime.timedelta(days=3), # Thursday
                            time = datetime.time(7, 30),
                            household = test_household,
                            user = test_user,
                            calories = 500)
        avg_calories = get_avg_week_calories(day)
        self.assertEqual(1000, avg_calories)
        # test for number of database queries here? depends entirely on
        # get_sum_day_calories so should perhaps only test it there

    def test_get_week_starts_in_month(self):
        # A normal month:
        month_start_date = datetime.datetime(2011, 11, 1, 0, 0)
        test_week_date_list = get_week_starts_in_month(month_start_date)
        expected_results = [datetime.datetime(2011, 10, 31, 0, 0),
                            datetime.datetime(2011, 11, 7, 0, 0),
                            datetime.datetime(2011, 11, 14, 0, 0),
                            datetime.datetime(2011, 11, 21, 0, 0),
                            datetime.datetime(2011, 11, 28, 0, 0)]
        self.assertEqual(test_week_date_list, expected_results)

        # December, to test moving into a new year
        month_start_date = datetime.datetime(2011, 12, 1, 0, 0)
        test_week_date_list = get_week_starts_in_month(month_start_date)
        expected_results = [datetime.datetime(2011, 11, 28, 0, 0),
                            datetime.datetime(2011, 12, 5, 0, 0),
                            datetime.datetime(2011, 12, 12, 0, 0),
                            datetime.datetime(2011, 12, 19, 0, 0),
                            datetime.datetime(2011, 12, 26, 0, 0)]
        self.assertEqual(test_week_date_list, expected_results)

    def test_week_bounds(self):
        # can't import _week_bounds here;
        # test it through MealWeekArchiveView instead
        pass

