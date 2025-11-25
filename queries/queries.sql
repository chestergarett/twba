select Gender,count(Gender) 
from [dbo].[SalesInteractions]
group by Gender

select top 5 * 
from [dbo].[SalesInteractions]
where TranscriptionText <> ''

select *
from [dbo].[SalesInteractions]
where InteractionID='19667439-5f9a-4c6d-99f4-718e58a57e53'