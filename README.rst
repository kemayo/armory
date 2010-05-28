======
Armory
======

Intro
-----

This python module includes some simple ways to fetch data from the WoW
armory. I wrote it back in late 2008, and haven't really touched it since,
but it still works.

It's incomplete. Patches are welcome. I may fix it up myself if I ever
remember what I was originally writing it for.

Usage
-----

The main finished part of ``armory`` is ``armory.get_character``. Like so:

>>> import armory
>>> retcon = get_character('us', 'Lothar', 'Retcon')
>>> retcon.name
u'Retcon'
>>> retcon.items[0]
<armory.EquippedItem object at 0x865e8ac>
>>> retcon.items[0].id
47674
>>> retcon.items[0].name
u'Helm of Thunderous Rampage'
