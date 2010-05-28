import re
import urllib2
import xml.dom.minidom

__author__ = 'David Lynch (kemayo at gmail dot com)'
__version__ = '1'
__copyright__ = 'Copyright (c) 2008 David Lynch'
__license__ = 'New BSD License'

_regions = {
    "US": "http://wowarmory.com",
    "EU": "http://eu.wowarmory.com",
}
_factions = {
    0: "Aliance",
    1: "Horde",
}

# This is a very useful URL for development: http://www.wowarmory.com/strings/en_US/strings.xml
# http://www.wowarmory.com/layout/item-tooltip.xsl
# http://www.wowarmory.com/layout/character-sheet.xsl
# http://www.wowarmory.com/js/character/functions.js
# http://www.wowarmory.com/js/ajaxtooltip.js

class Character(object):
    """Basic representation of a character

    You won't ever see a plain Character instance -- it just contains
    the common features of the various character types.
    """
    def __init__(self, dom):
        self.name = dom.getAttribute('name')
        self.character_class = dom.getAttribute('class')
        self.class_id = dom.getAttribute('classId')
        self.level = dom.getAttribute('level') and int(dom.getAttribute('level')) or 0
        self.race = dom.getAttribute('race')
        self.gender = dom.getAttribute('gender')
        self.guild = dom.getAttribute('guild') or dom.getAttribute('guildName') or False
        self.realm = dom.getAttribute('realm')
    def __eq__(self, other):
        return hasattr(other, 'realm') and hasattr(other, 'name') and (self.name == other.name) and (self.realm == other.realm)
    def __ne__(self, other):
        return not self.__eq__(other)
    def __lt__(self, other):
        return hasattr(other, 'level') and self.level < other.level
    def __le__(self, other):
        return hasattr(other, 'level') and self.level <= other.level
    def __gt__(self, other):
        return hasattr(other, 'level') and self.level > other.level
    def __ge__(self, other):
        return hasattr(other, 'level') and self.level >= other.level
    def __str__(self):
        if self.guild:
            return "%s <%s> (%s)" % (self.name, self.guild, self.realm)
        else:
            return "%s (%s)" % (self.name, self.realm)

class DetailedCharacter(Character):
    """Characters as portrayed on the character sheet
    
    Important: This character type expects a <characterInfo> node, which
    will contain a <character> node that gets passed to the Character __init__.
    """
    def __init__(self, dom):
        charnode = _getChildNodesByTagName(dom, 'character')[0]
        Character.__init__(self, charnode)

        self.last_modified = charnode.getAttribute("lastModified") # make this a date?
        self.arena_teams = [ArenaTeam(team) for team in dom.getElementsByTagName('arenaTeam')]
        details = dom.getElementsByTagName('characterTab')
        if details:
            # Check this because an armory cache miss will result in very minimal info
            # TODO: buffs, professions, title, knownTitles, talentSpecs, achievement summary
            details = details[0]
            self.bars = _simple_stat_extract(details, 'characterBars')

            talents = details.getElementsByTagName('talentSpec')[0]
            self.talents = (int(talents.getAttribute('treeOne')), int(talents.getAttribute('treeTwo')), int(talents.getAttribute('treeThree')),)
            
            self.base_stats = _simple_stat_extract(details, 'baseStats')
            self.resistances = _simple_stat_extract(details, 'resistances')
            self.melee = _simple_stat_extract(details, 'melee')
            self.ranged = _simple_stat_extract(details, 'ranged')
            self.defenses = _simple_stat_extract(details, 'defenses')
            
            spell = _getChildNodesByTagName(details, 'spell')[0]
            self.spell = {}
            self.spell['bonus_damage'] = _simple_stat_extract(spell, 'bonusDamage')
            self.spell['bonus_healing'] = _attributes(spell.getElementsByTagName('bonusHealing')[0])
            self.spell['hit_rating'] = _attributes(spell.getElementsByTagName('hitRating')[0])
            self.spell['crit_rating'] = _attributes(spell.getElementsByTagName('critChance')[0])
            self.spell['crit_chance'] = _simple_stat_extract(spell, 'critChance')
            self.spell['penetration'] = _attributes(spell.getElementsByTagName('penetration')[0])
            self.spell['mana_regen'] = _attributes(spell.getElementsByTagName('manaRegen')[0])
            
            self.items = [EquippedItem(item) for item in dom.getElementsByTagName('item')]
            self.glyphs = [Glyph(glyph) for glyph in dom.getElementsByTagName('glyph')]

            self.pvp = _simple_stat_extract(details, 'pvp')

class GuildCharacter(Character):
    """Characters as portrayed on the guild roster sheet"""
    def __init__(self, dom):
        Character.__init__(self, dom)
        key = dom.parentNode.parentNode.parentNode.getElementsByTagName('guildKey')[0]
        self.realm = key.getAttribute('realm')
        self.guild = key.getAttribute('name')
        self.faction = _factions.get(int(key.getAttribute('factionId')))

class ArenaTeamCharacter(Character):
    """Characters with extra PvP info"""
    def __init__(self, dom):
        Character.__init__(self, dom)
        team = dom.parentNode.parentNode
        self.faction = team.getAttribute('faction')
        self.realm = team.getAttribute('realm')
        self.battlegroup = team.getAttribute('battleGroup')

        self.contribution = dom.getAttribute('contribution')
        self.games_played = dom.getAttribute('gamesPlayed')
        self.games_won = dom.getAttribute('gamesWon')
        self.season_games_played = dom.getAttribute('seasonGamesPlayed')
        self.season_games_won = dom.getAttribute('seasonGamesWon')
        self.team_rank = dom.getAttribute('teamRank')

class CharacterContainer(object):
    """Stub for named collections of characters, like guilds or arena teams"""
    def __str__(self):
        return self.name
    def __eq__(self, other):
        if not (hasattr(other, 'realm') and hasattr(other, 'name')):
            return False
        return (self.realm == other.realm) and (self.name == other.name)
    def __len__(self):
        return len(self.members)
    def __iter__(self):
        return self.members.__iter__()

class ArenaTeam(CharacterContainer):
    def __init__(self, dom):
        self.name = dom.getAttribute('name')
        self.faction = dom.getAttribute('faction')
        self.realm = dom.getAttribute('realm')
        self.battlegroup = dom.getAttribute('battleGroup')
        self.ranking = dom.getAttribute('ranking')
        self.last_season_ranking = dom.getAttribute('lastSeasonRanking')
        self.rating = dom.getAttribute('rating')
        self.games_played = dom.getAttribute('gamesPlayed')
        self.games_won = dom.getAttribute('gamesWon')
        self.season_games_played = dom.getAttribute('seasonGamesPlayed')
        self.season_games_won = dom.getAttribute('seasonGamesWon')
        self.members = [ArenaTeamCharacter(c) for c in dom.getElementsByTagName('character')]
        self.emblem = _attributes(dom.getElementsByTagName('emblem')[0])

class Guild(CharacterContainer):
    def __init__(self, dom):
       self.name = dom.getAttribute('name')
       self.realm = dom.getAttribute('realm')
       self.faction = _factions.get(int(dom.getAttribute('factionId')))
       self.members = [GuildCharacter(c) for c in dom.getElementsByTagName('character')]

class Item(object):
    def __eq__(self, other):
        if not hasattr(other, 'id'):
            return False
        return self.id == other.id
    def __str__(self):
        return "item:%d" % self.id

class EquippedItem(Item):
    """The basic item information available on a character page."""
    def __init__(self, dom):
        # todo: work out what displayInfoId refers to, and if it should be included
        self.id = int(dom.getAttribute('id'))
        self.name = dom.getAttribute('name')
        self.slot = int(dom.getAttribute('slot'))
        self.icon = dom.getAttribute('icon') # a texture name like "inv_chest_plate_25"
        self.rarity = int(dom.getAttribute('rarity'))
        self.enchant = int(dom.getAttribute('permanentenchant')) # An id; can probably be mined futher from wowhead
        self.seed = int(dom.getAttribute('seed')) # I'm not actually sure what this *is*.
        self.random_properties = int(dom.getAttribute('randomPropertiesId')) # Again, not 100% sure.
        self.durability = int(dom.getAttribute('durability'))
        self.max_durability = int(dom.getAttribute('maxDurability'))
        self.gems = (int(dom.getAttribute('gem0Id')), int(dom.getAttribute('gem1Id')), int(dom.getAttribute('gem2Id')),)

class DetailedItem(Item):
    """From an item tooltip"""
    def __init__(self, dom):
        self.id = int(_getNodeTextByTag(dom, 'id'))
        self.name = _getNodeTextByTag(dom, 'name')
        self.icon = _getNodeTextByTag(dom, 'icon')
        self.quality = _getNodeTextByTag(dom, 'overallQualityId') # 0-5 for white-orange
        self.bonding = _getNodeTextByTag(dom, 'bonding') # 1=pickup, 2=equip, 3=use, 4/5=quest
        self.slot = _getNodeTextByTag(dom, 'inventoryType')
        self.item_class = (_getNodeTextByTag(dom, 'classId'), _getNodeTextByTag(dom, 'subclassName')) # e.g (4, 'Plate')

        #self.drop_rate = _getNodeTextByTag(dom, 

class Glyph(object):
    def __init__(self, dom):
        self.id = int(dom.getAttribute('id'))
        self.name = dom.getAttribute('name')
        self.icon = dom.getAttribute('icon')
        self.type = dom.getAttribute('type')
        self.effect = dom.getAttribute('effect')
    def __eq__(self, other):
        if not hasattr(other, 'id'):
            return False
        return self.id == other.id
    def __str__(self):
        return "glyph:%d" % self.id

class ArmoryException(Exception):
    pass

def _fetch_data(url):
    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent', 'armory.py (treat as Firefox/2.0.0.8)'),]
    request = opener.open(url)
    dom = xml.dom.minidom.parse(request)
    return dom.getElementsByTagName('page')[0]

def _getChildNodesByTagName(dom, tagName):
    return [node for node in dom.childNodes if node.nodeName == tagName]

def _getNodeText(node):
    text = []
    for n in node.childNodes:
        if n.nodeType == n.TEXT_NODE:
            text.append(n.data)
    return ''.join(text)

def _getNodeTextByTag(dom, tagName):
    nodes = dom.getElementsByTagName(tagName)
    if nodes:
        return _getNodeText(nodes[0])
    return ''

def _simple_stat_extract(dom, tagName):
    stats = {}
    node = dom.getElementsByTagName(tagName)
    if node:
        for n in node[0].childNodes:
            if hasattr(n, 'tagName'):
                stats[_decamel(n.tagName)] = _attributes(n)
    return stats

def _attributes(node):
    if len(node.attributes) > 1:
        stat = {}
        for attr in node.attributes.items():
            stat[_decamel(attr[0])] = _attr_to_correct_type(attr[1])
    else:
        stat = _attr_to_correct_type(node.attributes.item(0).value)
    return stat

def _attr_to_correct_type(s):
    if s.isdigit():
        return int(s)
    elif s.replace('.','').isdigit():
        return float(s)
    else:
        return s

def _decamel(s):
    """Converts 'camelCase' to 'camel_case'"""
    return re.sub(r'([a-z])([A-Z])', _decamel_replace, s)
    
def _decamel_replace(m):
    return '_'.join((m.group(1), m.group(2).lower()))

def get_character(region, realm, character):
    raw = _fetch_data("%s/character-sheet.xml?r=%s&n=%s" % (_regions.get(region.upper(), _regions['US']), realm.replace(' ', '+'), character))
    characterInfo = raw.getElementsByTagName('characterInfo')[0]
    if characterInfo.hasAttribute('errCode'):
        raise ArmoryException, characterInfo.getAttribute('errCode')
    return DetailedCharacter(characterInfo)

def get_item(itemid):
    raw = _fetch_data("%s/item-tooltip.xml?i=%d" % (_regions['US'], itemid))
    itemTooltips = raw.getElementsByTagName('itemTooltip')
    if len(itemTooltips) == 0:
        raise ArmoryException, "No item found (%d)" % itemid
    return DetailedItem(itemTooltips[0])
    #return itemTooltips[0]

if __name__ == "__main__":
    a = get_character('us', 'Lothar', 'Retcon')
    print a
