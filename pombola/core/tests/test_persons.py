import re
import datetime

from django.conf import settings
from django.core import mail
from django_webtest import WebTest
from django.test.client import Client
from django.test import TestCase

from django.contrib.auth.models import User

from pombola.core import models
import pombola.scorecards.models

class PersonTest(WebTest):
    def test_naming(self):        
        # create a test person
        person = models.Person(
            legal_name="Alfred Smith"
        )
        person.save()
        self.assertEqual( person.name, "Alfred Smith" )
        self.assertEqual( person.additional_names(), [] )

        # Add an alternative name
        person.add_alternative_name("Freddy Smith", name_to_use=True)
        self.assertEqual( person.name, "Freddy Smith" )
        self.assertEqual( person.additional_names(), [] )

        # Add yet another alternative name
        person.add_alternative_name("Fred Smith", name_to_use=True)
        self.assertEqual( person.name, "Fred Smith" )
        self.assertEqual( person.additional_names(), ['Freddy Smith'] )

        # Remove the first of those names:
        person.remove_alternative_name("Fred Smith")
        self.assertEqual( person.name, "Alfred Smith" )
        self.assertEqual( person.additional_names(), ['Freddy Smith'] )

        # Add yet another alternative name
        person.add_alternative_name("\n\nFred Smith\n\n", name_to_use=True)
        self.assertEqual( person.name, "Fred Smith" )
        self.assertEqual( person.additional_names(), ['Freddy Smith'] )

    def test_urls(self):
        person = models.Person(
            legal_name="Alfred Smith",
            slug='alfred-smith',
        )
        person.save()
        resp = self.app.get('/person/alfred-smith/')
        self.assertContains(resp, person.legal_name)

class PersonScorecardTest(TestCase):
    def setUp(self):    
        # Alf is a person, but with no particular position.
        self.alf = models.Person.objects.create(
            legal_name="Alfred Smith",
            slug='alfred_smith',
            )
        
        self.cat_contactability = pombola.scorecards.models.Category.objects.create(
            name='Contactability',
            slug='contactability',
            synopsis='How easy is it to get in contact with this person',
            description='Contactability description',
            )

        self.cat_ntacdf = pombola.scorecards.models.Category.objects.create(
            name='NTACDF',
            slug='ntacdf',
            synopsis='NTA constituency data',
            description='NTA constituency data description',
            )

        self.alf.scorecard_entries.create(
            category=self.cat_contactability,
            date=datetime.date(2010, 1, 1),
            remark="Very good!",
            score=1,
            )

        # Bob, however, is the MP for Bobsplace.
        self.bob = models.Person.objects.create(
            legal_name="Bob Jones",
            slug='bob_jones',
            )

        self.politician_title = models.PositionTitle.objects.create(
            name='MP',
            slug='mp',
            )

        self.nominated_politician_title = models.PositionTitle.objects.create(
            name='Nominated Member of Parliament',
            slug='nominated-member-parliament',
            )

        self.place_kind_constituency = models.PlaceKind.objects.create(
            name='Constituency',
            )

        self.bobs_place = models.Place.objects.create(
            name="Bob's Place",
            slug='bobs_place',
            kind=self.place_kind_constituency,
            )

        self.bobs_position = models.Position.objects.create(
            person=self.bob,
            place=self.bobs_place,
            category='political',
            title=self.politician_title,
            )
        
        # Bob is average at one thing
        self.bob.scorecard_entries.create(
            category=self.cat_contactability,
            date=datetime.date(2010, 1, 1),
            remark="Vaguely contactable if you know what you're doing.",
            score=0,
            )

        # Bob's constituency data is pretty bad though.
        self.bobs_place.scorecard_entries.create(
            category=self.cat_ntacdf,
            date=datetime.date(2010, 1, 1),
            remark="Nothing much left here, it's all been stolen.",
            score=-1,
            )

        # Charlie is a nominated MP with no constituency
        self.charlie = models.Person.objects.create(
            legal_name='Charlie Brown',
            slug='charlie_brown',
            )

        self.charlies_position = models.Position.objects.create(
            person=self.charlie,
            category='political',
            title=self.nominated_politician_title,
            )

    def testScorecardOverallNonMP(self):
        # import pdb;pdb.set_trace()
        assert self.alf.scorecard_overall() == 1
        assert self.alf.scorecard_overall_as_word() == 'good'

        self.alf.scorecard_entries.create(
            category=self.cat_ntacdf,
            date=datetime.date(2010, 1, 1),
            remark="Awful.",
            score=-1,
            )

        assert self.alf.scorecard_overall() == 0
        assert self.alf.scorecard_overall_as_word() == 'average'

    def testScorecardOverallMP(self):
        assert self.bob.scorecard_overall() == -0.5, "Bob's score: %s" %self.bob.scorecard_overall()
        assert self.bob.scorecard_overall_as_word() == 'bad', "Bob's word: %s" %self.bob.scorecard_overall_as_word()

    def testConstituencies(self):
        assert not self.alf.constituencies()
        assert len(self.bob.constituencies()) == 1, self.bob.constituencies()
        assert self.bob.constituencies()[0].slug == 'bobs_place'

    def testIsMP(self):
        assert self.bob.is_politician()
        assert not self.alf.is_politician()
        assert self.charlie.is_politician()
