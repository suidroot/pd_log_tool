from datetime import datetime
from django.db import models

def split_name(text_name):

    last, first = text_name.split(', ')
    split_first = first.split(" ")

    if len(split_first) > 1:
        name_dict = {
            'firstname' : split_first[0],
            'lastname' : last,
            'middlename' : split_first[1]
        }
    else:
        name_dict = {
            'firstname' : first,
            'lastname' : last,
            'middlename' : ''
        }

    return name_dict

class Municipality(models.Model):
    short_name = models.CharField(max_length=4, unique=True)
    display_text = models.TextField()
    city = models.TextField()
    state = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

class RecordType(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

class Disposition(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

    @classmethod
    def search_by_name(cls, display_text):

        results = cls.objects.filter(display_text=display_text)

        if not results.exists():
            return_val = None
        elif cls.objects.filter(display_text=display_text).count() > 1:
            raise("Duplicate Disposition Detected")
        else:
            return_val = results[0]

        return return_val

    @classmethod
    def get_or_create(cls, display_text):
        display_text = display_text.title()

        obj = cls.search_by_name(display_text)

        if not obj:
            obj = cls.create(display_text)
        
        return obj

    @classmethod
    def create(cls, display_text):
        display_text = display_text.title()
        obj = cls(display_text=display_text)
        obj.save()

        return obj

class DispatchType(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

    @classmethod
    def search_by_name(cls, display_text):

        results = cls.objects.filter(display_text=display_text)

        if not results.exists():
            return_val = None
        elif cls.objects.filter(display_text=display_text).count() > 1:
            raise("Duplicate Call Type Detected")
        else:
            return_val = results[0]

        return return_val

    @classmethod
    def get_or_create(cls, display_text):
        display_text = display_text.title()

        obj = cls.search_by_name(display_text)
        print(obj)

        if not obj:
            obj = cls.create(display_text)
        
        return obj

    @classmethod
    def create(cls, display_text):
        display_text = display_text.title()
        obj = cls(display_text=display_text)
        obj.save()

        return obj

class ArrestType(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

    @classmethod
    def search_by_name(cls, display_text):

        results = cls.objects.filter(display_text=display_text)

        if not cls.objects.filter(display_text=display_text).exists():
            results = None
        elif cls.objects.filter(display_text=display_text).count() > 1:
            results = None
        else:
            query_return = cls.objects.filter(display_text=display_text)
            return query_return[0]

        return results

    @classmethod
    def get_or_create(cls, display_text):
        display_text = display_text.title()

        obj = cls.search_by_name(display_text)

        if not obj:
            obj = cls.create(display_text)
        
        return obj

    @classmethod
    def create(cls, display_text):
        display_text = display_text.title()
        obj = cls(display_text=display_text)
        obj.save()
        return obj


class Charge(models.Model):
    display_text = models.TextField()

    def __str__(self):
        return f"{self.display_text}"

    @classmethod
    def search_by_name(cls, display_text):

        if not cls.objects.filter(display_text=display_text).exists():
            results = None
        elif cls.objects.filter(display_text=display_text).count() > 1:
            results = None
        else:
            query_return = cls.objects.filter(display_text=display_text)
            return query_return[0]

        return results

    @classmethod
    def get_or_create(cls, display_text):
        display_text = display_text.title()

        obj = cls.search_by_name(display_text)

        if not obj:
            obj = cls.create(display_text)
        
        return obj

    @classmethod
    def create(cls, display_text):
        display_text = display_text.title()
        obj = cls(display_text=display_text)
        obj.save()
        return obj

class Officer(models.Model):
    municipality = models.ForeignKey(Municipality, on_delete=models.DO_NOTHING)
    firstname = models.TextField()
    lastname = models.TextField()
    middlename = models.TextField(default='')

    first_seen = models.DateTimeField(auto_now_add=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lastname}, {self.firstname}"

    @classmethod
    def search_by_name(cls, municipality, firstname, lastname, middlename=None):

        if not cls.objects.filter(municipality=municipality, firstname=firstname, \
                                  lastname=lastname).exists():
            results = None
        elif cls.objects.filter(municipality=municipality, firstname=firstname, \
                                  lastname=lastname).count() > 1:
            results = None
        else:
            query_return = cls.objects.filter(municipality=municipality, firstname=firstname, \
                                  lastname=lastname)
            return query_return[0]

        return results

    @classmethod
    def get_or_create(cls, municipality=municipality, firstname=firstname, \
                                  lastname=lastname, middlename=None):

        firstname = firstname.capitalize()
        lastname = lastname.capitalize()

        obj = cls.search_by_name(municipality, firstname, lastname)

        if not obj:
            obj = cls.create(municipality, firstname, lastname)
        
        return obj

    @classmethod
    def create(cls, municipality, firstname, lastname, middlename=None, \
               first_seen=None):

        firstname = firstname.capitalize()
        lastname = lastname.capitalize()
        
        if not first_seen:
            first_seen = datetime.now()

        if middlename:
            middlename = middlename.capitalize()
            obj = cls(
                firstname=firstname, 
                lastname=lastname, 
                middlename=middlename,
                first_seen=first_seen
            )
        else:
            obj = cls(
                municipality=municipality,
                firstname=firstname, 
                lastname=lastname,
                first_seen=first_seen
            )

        obj.save()
        return obj


class Arrestee(models.Model):
    firstname = models.TextField()
    lastname = models.TextField()
    middlename = models.TextField(default='')
    home_city = models.TextField()
    age = models.IntegerField()
    first_seen = models.DateTimeField(auto_now_add=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.firstname} {self.lastname} {self.middlename}"

    @classmethod
    def search_by_name(cls, firstname, lastname, middlename=None):

        if not cls.objects.filter(firstname=firstname, lastname=lastname).exists():
            results = None
        elif cls.objects.filter(firstname=firstname, lastname=lastname).count() > 1:
            results = None
        else:
            query_return = cls.objects.filter(firstname=firstname, lastname=lastname)
            return query_return[0]

        return results

    @classmethod
    def get_or_create(cls, arrestee_dict):
        firstname = arrestee_dict['firstname'].capitalize()
        lastname = arrestee_dict['lastname'].capitalize()
        middlename = arrestee_dict['middlename'].capitalize()

        obj = cls.search_by_name(firstname, lastname, middlename)

        if not obj:
            obj = cls.create(arrestee_dict)
        
        return obj

    @classmethod
    def create(cls, arrestee_dict, first_seen=None):

        firstname = arrestee_dict['firstname'].capitalize()
        lastname = arrestee_dict['lastname'].capitalize()
        
        if not first_seen:
            first_seen = datetime.now()

        middlename = arrestee_dict.get('middlename', None)

        if middlename:
            middlename = middlename.capitalize()
            obj = cls(
                firstname=firstname, 
                lastname=lastname, 
                middlename=middlename,
                home_city = arrestee_dict['home_city'].title(),
                age = int(arrestee_dict['age']),
                first_seen=first_seen
            )
        else:
            obj = cls(
                firstname=firstname, 
                lastname=lastname, 
                home_city = arrestee_dict['home_city'].title(),
                age = int(arrestee_dict['age']),
                first_seen=first_seen
            )

        obj.save()

        return obj

class PoliceLog(models.Model):

    municipality = models.ForeignKey(Municipality, on_delete=models.DO_NOTHING)
    record_type = models.ForeignKey(RecordType, on_delete=models.DO_NOTHING)
    dispatch_number = models.IntegerField(unique=True, null=True)
    datetime_start = models.DateTimeField(null=True)
    datetime_stop = models.DateTimeField(null=True)
    dispatch_type = models.ForeignKey(DispatchType, on_delete=models.DO_NOTHING, null=True)
    disposition = models.ForeignKey(Disposition, on_delete=models.DO_NOTHING, null=True)
    officer = models.ForeignKey(Officer, on_delete=models.DO_NOTHING)
    arrestee = models.ForeignKey(Arrestee, on_delete=models.DO_NOTHING, null=True) # Table has name, home city and age
    charge = models.ManyToManyField(Charge) # can be multiple
    arrest_type = models.ForeignKey(ArrestType, on_delete=models.DO_NOTHING, null=True)
    address = models.TextField() # Violation Location
    date_added = models.DateTimeField(auto_now_add=True)


    @classmethod
    def create_dispatch(cls, media_log):
        municipality = Municipality.objects.get(short_name=media_log['muni_short'])
        record_type = RecordType.objects.get(display_text='Dispatch')
        dispatch_number = int(media_log['dispatch_number'])

        # 09/21/2023 
        # 02:15 AM
        start_str = media_log['dispatch_start'].replace('\n', ' ')
        dispatch_start = datetime.strptime(start_str, "%m/%d/%Y %I:%M %p")

        stop_str = media_log['dispatch_stop'].replace('\n', ' ')
        dispatch_stop = datetime.strptime(stop_str, "%m/%d/%Y %I:%M %p")
        
        dispatch_type = DispatchType.get_or_create(media_log['dispatch_type'])
        dispatch_address = media_log['address'].title()

        if media_log['officer'] == '':
            officer = Officer.get_or_create(municipality, 'unknown', 'unknown')
        else:
            officer_name = split_name(media_log['officer'])
            officer = Officer.get_or_create(municipality, officer_name['firstname'], officer_name['lastname'])

        obj = cls(
            municipality=municipality,
            record_type=record_type,
            dispatch_number=dispatch_number,
            datetime_start=dispatch_start,
            datetime_stop=dispatch_stop,
            dispatch_type=dispatch_type,
            address=dispatch_address,
            officer=officer
        )
        obj.save()

        return obj


    @classmethod
    def create_arrest(cls, arrest_log):
        municipality = Municipality.objects.get(short_name=arrest_log['muni_short'])
        record_type = RecordType.objects.get(display_text='Arrest')
        # 09/21/2023 
        # 02:15 AM
        arrest_str = arrest_log['arrest_date'].replace('\n', ' ')
        arrest_date = datetime.strptime(arrest_str, "%m/%d/%y %I:%M %p")
        arrestee = Arrestee.get_or_create(arrest_log['arrestee'])
        arrest_type = ArrestType.get_or_create(arrest_log['arrest_type'])
        
        charges = []
        if isinstance(arrest_log['charge'], list):
            for charge_item in arrest_log['charge']:
                charge = Charge.get_or_create(charge_item)
                charges.append(charge)
        else:
            charges = Charge.get_or_create(arrest_log['charge'])

        officer_name = split_name(arrest_log['officer'])
        officer = Officer.get_or_create(municipality, officer_name['firstname'], officer_name['lastname'])

        arrest_address = arrest_log['address'].title()

        obj = cls(
            municipality=municipality,
            record_type=record_type,
            datetime_start=arrest_date,
            arrestee=arrestee,
            arrest_type=arrest_type,
            address=arrest_address,
            officer=officer,
        )

        obj.save()
        obj.charge.set(charges)
        obj.save()


        return obj