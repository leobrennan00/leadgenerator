
import csv
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Sends emails to all email addresses listed in a CSV file'

    def handle(self, *args, **kwargs):
        # Open the CSV file containing the emails
        with open('emails/electrician_emails.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)

            # Loop through each email address in the CSV
            for row in reader:
                email = row[0]

                if email:  # Ensure the email is not empty
                    self.send_email_to(email)

    def send_email_to(self, email):
        subject = 'Hoping to help'
        message = ('Hi hope all is well, I found your email from the website so not sure if you guys even respond through it but thought I would reach out.\n\n'
                   "I'm a Sligo man who graduated from Computer Science recently and is looking to help out electricians around the country like yourself."
                   " I'm not trying to sell you anything, I'm just wondering is there any aspects of your job such as day to day admin tasks that are far too tedious and take up some of your time that could be used more efficiently?"
                   " This could be anything from invoicing, quotes, following up on leads, or anything at all you could think of that is frankly a bit of a pain!\n\n"
                   "I'd love to hear any ideas you'd have and if you'd even like to give me a phone call or set up a zoom meeting that would be great also."
                   " Brass tax, I'm hoping to develop something that can help you guys save more time, make more money, and in the end make things a bit easier in your day to day work."
                   " My phone number is 0830682621 and you can contact me through this email either, looking forward to hearing back from you!\n\n"
                   "Best Regards,\n\n"
                   "Leo Brennan Tohill")
        from_email = settings.EMAIL_HOST_USER  # Sender email
        recipient_list = [email]  # Recipient email list

        try:
            # Send the email
            send_mail(subject, message, from_email, recipient_list)
            self.stdout.write(self.style.SUCCESS(f'Successfully sent email to {email}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email to {email}. Error: {str(e)}'))