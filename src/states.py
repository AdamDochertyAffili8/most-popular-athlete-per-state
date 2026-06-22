"""
Lookup tables and helpers for the NYT athlete analysis.
  - SPORTS_SUBJECTS   set of NYT subject tags that indicate a sports article
  - glocation_to_state()   maps a NYT glocation tag to a US state name (or None)
  - clean_person_name()    strips NYT birth-year suffixes from persons tags
"""

import re

# People who regularly appear in sports articles but are not athletes.
# NYT persons tags use "Last, First" format. Extend this set as new cases emerge.
NON_ATHLETES: set[str] = {
    # Politicians
    "Trump, Donald J", "Trump, Donald J.",
    "Obama, Barack", "Biden, Joseph R Jr",
    "Pence, Mike", "Pataki, George E",
    # Team owners / executives
    "Prokhorov, Mikhail D",
    "Steinbrenner, George M 3d",
    "McMahon, Linda E", "McMahon, Vince",
    "Kroenke, Stan",
    "Cuban, Mark",
    "Sterling, Donald T",
    # Sports commissioners / officials
    "Stern, David", "Silver, Adam",
    "Goodell, Roger",
    "Manfred, Robert D Jr",
    "Bettman, Gary B",
    # Coaches / managers (comment out any you want included)
    # Journalists / media figures commonly tagged in sports articles
    "Madoff, Bernard L",
}

SPORTS_SUBJECTS = {
    # Team sports
    "Baseball", "Basketball", "Football", "Soccer", "Hockey", "Ice Hockey",
    "Softball", "Volleyball", "Lacrosse", "Rugby Football", "Field Hockey",
    "Water Polo", "Polo", "Cricket",
    # Individual sports
    "Tennis", "Golf", "Swimming", "Boxing", "Wrestling", "Gymnastics",
    "Track and Field", "Cross-Country Running", "Cycling",
    "Skiing and Ski Jumping", "Figure Skating", "Speed Skating",
    "Snowboarding", "Bobsledding", "Luge", "Biathlon", "Triathlon",
    "Rowing", "Sailing", "Equestrian Events", "Horse Racing",
    "Auto Racing", "Motorcycle Racing", "Bowling", "Archery",
    "Fencing (Sport)", "Shooting (Sport)", "Weight Lifting", "Weightlifting",
    "Martial Arts", "Mixed Martial Arts", "Surfing", "Skateboarding",
    "Diving", "Badminton", "Table Tennis", "Squash (Sport)",
    # Events / competitions
    "Olympics", "Olympic Games", "Paralympic Games", "Winter Olympics",
    "World Series", "Super Bowl", "Stanley Cup", "NBA Playoffs",
    "NCAA Basketball Tournament", "College Football", "College Basketball",
    "Little League Baseball", "Draft (Sports)", "Free Agency (Sports)",
    # Leagues / organisations
    "National Football League", "National Basketball Association",
    "Major League Baseball", "National Hockey League",
    "Major League Soccer", "Women's National Basketball Association",
    "National Collegiate Athletic Association",
}

# NYT parenthetical abbreviations → state name
_ABBR: dict[str, str] = {
    "ala": "Alabama", "alaska": "Alaska", "ariz": "Arizona", "ark": "Arkansas",
    "calif": "California", "colo": "Colorado", "conn": "Connecticut", "del": "Delaware",
    "fla": "Florida", "ga": "Georgia", "hawaii": "Hawaii", "idaho": "Idaho",
    "ill": "Illinois", "ind": "Indiana", "iowa": "Iowa", "kan": "Kansas",
    "ky": "Kentucky", "la": "Louisiana", "maine": "Maine", "md": "Maryland",
    "mass": "Massachusetts", "mich": "Michigan", "minn": "Minnesota",
    "miss": "Mississippi", "mo": "Missouri", "mont": "Montana", "neb": "Nebraska",
    "nev": "Nevada", "n.h": "New Hampshire", "nh": "New Hampshire",
    "n.j": "New Jersey",  "nj": "New Jersey",
    "n.m": "New Mexico",  "nm": "New Mexico",
    "n.y": "New York",    "ny": "New York",
    "n.c": "North Carolina", "nc": "North Carolina",
    "n.d": "North Dakota",   "nd": "North Dakota",
    "ohio": "Ohio", "okla": "Oklahoma", "ore": "Oregon", "pa": "Pennsylvania",
    "r.i": "Rhode Island",   "ri": "Rhode Island",
    "s.c": "South Carolina", "sc": "South Carolina",
    "s.d": "South Dakota",   "sd": "South Dakota",
    "tenn": "Tennessee", "tex": "Texas", "utah": "Utah", "vt": "Vermont",
    "va": "Virginia", "wash": "Washington",
    "w.va": "West Virginia", "wva": "West Virginia",
    "wis": "Wisconsin", "wyo": "Wyoming",
    "d.c": "District of Columbia", "dc": "District of Columbia",
}

# Full state names (and common NYT variants) → canonical state name
_STATE_NAMES: dict[str, str] = {
    "alabama": "Alabama", "alaska": "Alaska", "arizona": "Arizona",
    "arkansas": "Arkansas", "california": "California", "colorado": "Colorado",
    "connecticut": "Connecticut", "delaware": "Delaware", "florida": "Florida",
    "georgia": "Georgia", "hawaii": "Hawaii", "idaho": "Idaho",
    "illinois": "Illinois", "indiana": "Indiana", "iowa": "Iowa",
    "kansas": "Kansas", "kentucky": "Kentucky", "louisiana": "Louisiana",
    "maine": "Maine", "maryland": "Maryland", "massachusetts": "Massachusetts",
    "michigan": "Michigan", "minnesota": "Minnesota", "mississippi": "Mississippi",
    "missouri": "Missouri", "montana": "Montana", "nebraska": "Nebraska",
    "nevada": "Nevada", "new hampshire": "New Hampshire", "new jersey": "New Jersey",
    "new mexico": "New Mexico",
    "new york": "New York", "new york state": "New York", "new york (state)": "New York",
    "north carolina": "North Carolina", "north dakota": "North Dakota",
    "ohio": "Ohio", "oklahoma": "Oklahoma", "oregon": "Oregon",
    "pennsylvania": "Pennsylvania", "rhode island": "Rhode Island",
    "south carolina": "South Carolina", "south dakota": "South Dakota",
    "tennessee": "Tennessee", "texas": "Texas", "utah": "Utah",
    "vermont": "Vermont", "virginia": "Virginia",
    "washington": "Washington", "washington state": "Washington",
    "washington (state)": "Washington",
    "west virginia": "West Virginia", "wisconsin": "Wisconsin", "wyoming": "Wyoming",
    "district of columbia": "District of Columbia",
}

# Major US cities → state (covers the most common NYT city-level glocations)
_CITIES: dict[str, str] = {
    # NY metro
    "new york city": "New York", "manhattan": "New York", "brooklyn": "New York",
    "the bronx": "New York", "bronx": "New York", "queens": "New York",
    "staten island": "New York", "buffalo": "New York", "rochester": "New York",
    "syracuse": "New York", "albany": "New York", "yonkers": "New York",
    # NJ
    "newark": "New Jersey", "jersey city": "New Jersey",
    "east rutherford": "New Jersey", "trenton": "New Jersey", "camden": "New Jersey",
    # CA
    "los angeles": "California", "san francisco": "California",
    "san diego": "California", "san jose": "California",
    "fresno": "California", "sacramento": "California", "long beach": "California",
    "oakland": "California", "bakersfield": "California", "anaheim": "California",
    "santa ana": "California", "riverside": "California", "stockton": "California",
    "chula vista": "California", "fremont": "California", "irvine": "California",
    "san bernardino": "California", "modesto": "California", "oxnard": "California",
    "fontana": "California", "moreno valley": "California", "glendale": "California",
    "santa clarita": "California", "garden grove": "California",
    "oceanside": "California", "rancho cucamonga": "California",
    "hayward": "California", "corona": "California",
    "salinas": "California", "sunnyvale": "California",
    "torrance": "California", "pasadena": "California",
    "orange": "California", "santa barbara": "California",
    "stanford": "California",
    # IL
    "chicago": "Illinois", "aurora": "Illinois", "joliet": "Illinois",
    "rockford": "Illinois", "springfield": "Illinois",
    # TX
    "houston": "Texas", "san antonio": "Texas", "dallas": "Texas",
    "austin": "Texas", "fort worth": "Texas", "el paso": "Texas",
    "arlington": "Texas", "corpus christi": "Texas", "laredo": "Texas",
    "garland": "Texas", "irving": "Texas", "lubbock": "Texas",
    "plano": "Texas", "henderson": "Texas",
    # FL
    "jacksonville": "Florida", "miami": "Florida", "tampa": "Florida",
    "orlando": "Florida", "st. petersburg": "Florida", "hialeah": "Florida",
    "tallahassee": "Florida", "fort lauderdale": "Florida",
    "pembroke pines": "Florida", "cape coral": "Florida",
    # PA
    "philadelphia": "Pennsylvania", "pittsburgh": "Pennsylvania",
    "allentown": "Pennsylvania",
    # OH
    "columbus": "Ohio", "cleveland": "Ohio", "cincinnati": "Ohio",
    "toledo": "Ohio", "akron": "Ohio", "dayton": "Ohio",
    # GA
    "atlanta": "Georgia", "savannah": "Georgia", "augusta": "Georgia",
    # NC
    "charlotte": "North Carolina", "raleigh": "North Carolina",
    "greensboro": "North Carolina", "durham": "North Carolina",
    "winston-salem": "North Carolina",
    # WA
    "seattle": "Washington", "spokane": "Washington", "tacoma": "Washington",
    # CO
    "denver": "Colorado", "colorado springs": "Colorado",
    "aurora": "Colorado", "fort collins": "Colorado",
    # AZ
    "phoenix": "Arizona", "tucson": "Arizona", "scottsdale": "Arizona",
    "chandler": "Arizona", "glendale": "Arizona", "tempe": "Arizona",
    "gilbert": "Arizona",
    # IN
    "indianapolis": "Indiana",
    # TN
    "nashville": "Tennessee", "memphis": "Tennessee",
    "knoxville": "Tennessee", "clarksville": "Tennessee",
    # OK
    "oklahoma city": "Oklahoma", "tulsa": "Oklahoma",
    # NV
    "las vegas": "Nevada", "henderson": "Nevada", "reno": "Nevada",
    # KY
    "louisville": "Kentucky", "lexington": "Kentucky",
    # OR
    "portland": "Oregon", "eugene": "Oregon",
    # MD
    "baltimore": "Maryland",
    # WI
    "milwaukee": "Wisconsin", "madison": "Wisconsin", "green bay": "Wisconsin",
    # NM
    "albuquerque": "New Mexico",
    # NE
    "omaha": "Nebraska", "lincoln": "Nebraska",
    # MN
    "minneapolis": "Minnesota", "st. paul": "Minnesota", "saint paul": "Minnesota",
    "st paul": "Minnesota",
    # MO
    "kansas city": "Missouri", "st. louis": "Missouri",
    "saint louis": "Missouri", "st louis": "Missouri",
    "springfield": "Missouri",
    # LA
    "new orleans": "Louisiana", "baton rouge": "Louisiana",
    "shreveport": "Louisiana",
    # MI
    "detroit": "Michigan", "grand rapids": "Michigan",
    # VA
    "virginia beach": "Virginia", "norfolk": "Virginia",
    "chesapeake": "Virginia", "richmond": "Virginia",
    # SC
    "columbia": "South Carolina", "charleston": "South Carolina",
    # AL
    "birmingham": "Alabama", "montgomery": "Alabama",
    "mobile": "Alabama", "huntsville": "Alabama",
    # IA
    "des moines": "Iowa",
    # AR
    "little rock": "Arkansas",
    # MA
    "boston": "Massachusetts", "worcester": "Massachusetts",
    "springfield": "Massachusetts", "cambridge": "Massachusetts",
    "foxborough": "Massachusetts", "foxboro": "Massachusetts",
    "new haven": "Connecticut",
    # CT
    "hartford": "Connecticut", "bridgeport": "Connecticut",
    "stamford": "Connecticut",
    # RI
    "providence": "Rhode Island",
    # NH
    "manchester": "New Hampshire", "concord": "New Hampshire",
    # ID
    "boise": "Idaho",
    # UT
    "salt lake city": "Utah", "provo": "Utah",
    # HI
    "honolulu": "Hawaii",
    # AK
    "anchorage": "Alaska", "fairbanks": "Alaska",
    # NJ (sports venues)
    "princeton": "New Jersey",
    # DC
    "washington": "District of Columbia",
}

# Maps NYT subject tags to broad sport categories used for map colouring
SPORT_CATEGORIES: dict[str, str] = {
    # Football
    "Football": "Football", "National Football League": "Football",
    "College Football": "Football", "Super Bowl": "Football",
    "Draft (Sports)": "Football",
    # Baseball
    "Baseball": "Baseball", "Major League Baseball": "Baseball",
    "World Series": "Baseball", "Little League Baseball": "Baseball",
    "Softball": "Baseball",
    # Basketball
    "Basketball": "Basketball", "National Basketball Association": "Basketball",
    "College Basketball": "Basketball", "NCAA Basketball Tournament": "Basketball",
    "NBA Playoffs": "Basketball", "Women's National Basketball Association": "Basketball",
    # Hockey
    "Hockey": "Hockey", "Ice Hockey": "Hockey",
    "National Hockey League": "Hockey", "Stanley Cup": "Hockey",
    # Soccer
    "Soccer": "Soccer", "Major League Soccer": "Soccer",
    # Tennis
    "Tennis": "Tennis",
    # Golf
    "Golf": "Golf",
    # Boxing / MMA
    "Boxing": "Boxing/MMA", "Mixed Martial Arts": "Boxing/MMA",
    "Martial Arts": "Boxing/MMA", "Wrestling": "Boxing/MMA",
    # Olympics
    "Olympics": "Olympics", "Olympic Games": "Olympics",
    "Winter Olympics": "Olympics", "Paralympic Games": "Olympics",
    # Auto Racing
    "Auto Racing": "Auto Racing", "Automobile Racing": "Auto Racing",
    # Horse Racing
    "Horse Racing": "Horse Racing",
    # Track & Field / Swimming
    "Track and Field": "Track & Field", "Swimming": "Track & Field",
    "Gymnastics": "Track & Field", "Cycling": "Track & Field",
}

# Sports team name → state (covers pro leagues + notable college programs, 2000-2026)
TEAM_STATE: dict[str, str] = {
    # ── MLB ──────────────────────────────────────────────────────────────────
    "Arizona Diamondbacks": "Arizona",
    "Atlanta Braves": "Georgia",
    "Baltimore Orioles": "Maryland",
    "Boston Red Sox": "Massachusetts",
    "Chicago Cubs": "Illinois",
    "Chicago White Sox": "Illinois",
    "Cincinnati Reds": "Ohio",
    "Cleveland Indians": "Ohio",
    "Cleveland Guardians": "Ohio",
    "Colorado Rockies": "Colorado",
    "Detroit Tigers": "Michigan",
    "Houston Astros": "Texas",
    "Kansas City Royals": "Missouri",
    "Los Angeles Angels": "California",
    "Los Angeles Angels of Anaheim": "California",
    "Anaheim Angels": "California",
    "Los Angeles Dodgers": "California",
    "Miami Marlins": "Florida",
    "Florida Marlins": "Florida",
    "Milwaukee Brewers": "Wisconsin",
    "Minnesota Twins": "Minnesota",
    "New York Mets": "New York",
    "New York Yankees": "New York",
    "Oakland Athletics": "California",
    "Philadelphia Phillies": "Pennsylvania",
    "Pittsburgh Pirates": "Pennsylvania",
    "San Diego Padres": "California",
    "San Francisco Giants": "California",
    "Seattle Mariners": "Washington",
    "St. Louis Cardinals": "Missouri",
    "Tampa Bay Rays": "Florida",
    "Tampa Bay Devil Rays": "Florida",
    "Texas Rangers": "Texas",
    "Washington Nationals": "District of Columbia",
    # ── NBA ──────────────────────────────────────────────────────────────────
    "Atlanta Hawks": "Georgia",
    "Boston Celtics": "Massachusetts",
    "Brooklyn Nets": "New York",
    "New Jersey Nets": "New Jersey",
    "Charlotte Hornets": "North Carolina",
    "Charlotte Bobcats": "North Carolina",
    "Chicago Bulls": "Illinois",
    "Cleveland Cavaliers": "Ohio",
    "Dallas Mavericks": "Texas",
    "Denver Nuggets": "Colorado",
    "Detroit Pistons": "Michigan",
    "Golden State Warriors": "California",
    "Houston Rockets": "Texas",
    "Indiana Pacers": "Indiana",
    "Los Angeles Clippers": "California",
    "Los Angeles Lakers": "California",
    "Memphis Grizzlies": "Tennessee",
    "Miami Heat": "Florida",
    "Milwaukee Bucks": "Wisconsin",
    "Minnesota Timberwolves": "Minnesota",
    "New Orleans Pelicans": "Louisiana",
    "New Orleans Hornets": "Louisiana",
    "New Orleans/Oklahoma City Hornets": "Louisiana",
    "New York Knicks": "New York",
    "Oklahoma City Thunder": "Oklahoma",
    "Orlando Magic": "Florida",
    "Philadelphia 76ers": "Pennsylvania",
    "Phoenix Suns": "Arizona",
    "Portland Trail Blazers": "Oregon",
    "Sacramento Kings": "California",
    "San Antonio Spurs": "Texas",
    "Seattle SuperSonics": "Washington",
    "Utah Jazz": "Utah",
    "Washington Wizards": "District of Columbia",
    "Washington Bullets": "District of Columbia",
    # ── NFL ──────────────────────────────────────────────────────────────────
    "Arizona Cardinals": "Arizona",
    "Atlanta Falcons": "Georgia",
    "Baltimore Ravens": "Maryland",
    "Buffalo Bills": "New York",
    "Carolina Panthers": "North Carolina",
    "Chicago Bears": "Illinois",
    "Cincinnati Bengals": "Ohio",
    "Cleveland Browns": "Ohio",
    "Dallas Cowboys": "Texas",
    "Denver Broncos": "Colorado",
    "Detroit Lions": "Michigan",
    "Green Bay Packers": "Wisconsin",
    "Houston Texans": "Texas",
    "Indianapolis Colts": "Indiana",
    "Jacksonville Jaguars": "Florida",
    "Kansas City Chiefs": "Missouri",
    "Las Vegas Raiders": "Nevada",
    "Oakland Raiders": "California",
    "Los Angeles Chargers": "California",
    "San Diego Chargers": "California",
    "Los Angeles Rams": "California",
    "St. Louis Rams": "Missouri",
    "Miami Dolphins": "Florida",
    "Minnesota Vikings": "Minnesota",
    "New England Patriots": "Massachusetts",
    "New Orleans Saints": "Louisiana",
    "New York Giants": "New York",
    "New York Jets": "New York",
    "Philadelphia Eagles": "Pennsylvania",
    "Pittsburgh Steelers": "Pennsylvania",
    "San Francisco 49ers": "California",
    "Seattle Seahawks": "Washington",
    "Tampa Bay Buccaneers": "Florida",
    "Tennessee Titans": "Tennessee",
    "Tennessee Oilers": "Tennessee",
    "Houston Oilers": "Texas",
    "Washington Redskins": "District of Columbia",
    "Washington Football Team": "District of Columbia",
    "Washington Commanders": "District of Columbia",
    # ── NHL ──────────────────────────────────────────────────────────────────
    "Anaheim Ducks": "California",
    "Mighty Ducks of Anaheim": "California",
    "Arizona Coyotes": "Arizona",
    "Phoenix Coyotes": "Arizona",
    "Utah Hockey Club": "Utah",
    "Atlanta Thrashers": "Georgia",
    "Boston Bruins": "Massachusetts",
    "Buffalo Sabres": "New York",
    "Carolina Hurricanes": "North Carolina",
    "Hartford Whalers": "Connecticut",
    "Chicago Blackhawks": "Illinois",
    "Colorado Avalanche": "Colorado",
    "Columbus Blue Jackets": "Ohio",
    "Dallas Stars": "Texas",
    "Detroit Red Wings": "Michigan",
    "Florida Panthers": "Florida",
    "Los Angeles Kings": "California",
    "Minnesota Wild": "Minnesota",
    "Minnesota North Stars": "Minnesota",
    "Nashville Predators": "Tennessee",
    "New Jersey Devils": "New Jersey",
    "New York Islanders": "New York",
    "New York Rangers": "New York",
    "Philadelphia Flyers": "Pennsylvania",
    "Pittsburgh Penguins": "Pennsylvania",
    "San Jose Sharks": "California",
    "Seattle Kraken": "Washington",
    "St. Louis Blues": "Missouri",
    "Tampa Bay Lightning": "Florida",
    "Vegas Golden Knights": "Nevada",
    "Washington Capitals": "District of Columbia",
    # ── MLS ──────────────────────────────────────────────────────────────────
    "Austin FC": "Texas",
    "Charlotte FC": "North Carolina",
    "Chicago Fire": "Illinois",
    "Chicago Fire FC": "Illinois",
    "Colorado Rapids": "Colorado",
    "Columbus Crew": "Ohio",
    "D.C. United": "District of Columbia",
    "FC Dallas": "Texas",
    "Dallas Burn": "Texas",
    "Houston Dynamo": "Texas",
    "Inter Miami CF": "Florida",
    "LA Galaxy": "California",
    "Los Angeles FC": "California",
    "Minnesota United": "Minnesota",
    "Nashville SC": "Tennessee",
    "New England Revolution": "Massachusetts",
    "New York City FC": "New York",
    "New York Red Bulls": "New York",
    "New York/New Jersey MetroStars": "New York",
    "Orlando City": "Florida",
    "Philadelphia Union": "Pennsylvania",
    "Portland Timbers": "Oregon",
    "Real Salt Lake": "Utah",
    "San Jose Earthquakes": "California",
    "Seattle Sounders FC": "Washington",
    "Sporting Kansas City": "Missouri",
    "Kansas City Wizards": "Missouri",
    "St. Louis City SC": "Missouri",
    # ── NCAA — SEC ───────────────────────────────────────────────────────────
    "Alabama Crimson Tide": "Alabama",
    "Auburn Tigers": "Alabama",
    "Tennessee Volunteers": "Tennessee",
    "Georgia Bulldogs": "Georgia",
    "Florida Gators": "Florida",
    "LSU Tigers": "Louisiana",
    "Ole Miss Rebels": "Mississippi",
    "Mississippi State Bulldogs": "Mississippi",
    "Arkansas Razorbacks": "Arkansas",
    "South Carolina Gamecocks": "South Carolina",
    "Kentucky Wildcats": "Kentucky",
    "Vanderbilt Commodores": "Tennessee",
    "Missouri Tigers": "Missouri",
    "Texas A&M Aggies": "Texas",
    # ── NCAA — Big Ten ────────────────────────────────────────────────────────
    "Michigan Wolverines": "Michigan",
    "Ohio State Buckeyes": "Ohio",
    "Penn State Nittany Lions": "Pennsylvania",
    "Wisconsin Badgers": "Wisconsin",
    "Minnesota Golden Gophers": "Minnesota",
    "Iowa Hawkeyes": "Iowa",
    "Nebraska Cornhuskers": "Nebraska",
    "Illinois Fighting Illini": "Illinois",
    "Indiana Hoosiers": "Indiana",
    "Purdue Boilermakers": "Indiana",
    "Northwestern Wildcats": "Illinois",
    "Michigan State Spartans": "Michigan",
    "Maryland Terrapins": "Maryland",
    "Rutgers Scarlet Knights": "New Jersey",
    # ── NCAA — Big 12 ─────────────────────────────────────────────────────────
    "Oklahoma Sooners": "Oklahoma",
    "Oklahoma State Cowboys": "Oklahoma",
    "Texas Longhorns": "Texas",
    "Texas Tech Red Raiders": "Texas",
    "Baylor Bears": "Texas",
    "TCU Horned Frogs": "Texas",
    "Kansas Jayhawks": "Kansas",
    "Kansas State Wildcats": "Kansas",
    "Iowa State Cyclones": "Iowa",
    "West Virginia Mountaineers": "West Virginia",
    # ── NCAA — ACC ────────────────────────────────────────────────────────────
    "Duke Blue Devils": "North Carolina",
    "North Carolina Tar Heels": "North Carolina",
    "NC State Wolfpack": "North Carolina",
    "Virginia Cavaliers": "Virginia",
    "Virginia Tech Hokies": "Virginia",
    "Clemson Tigers": "South Carolina",
    "Florida State Seminoles": "Florida",
    "Miami Hurricanes": "Florida",
    "Boston College Eagles": "Massachusetts",
    "Notre Dame Fighting Irish": "Indiana",
    "Syracuse Orange": "New York",
    "Pittsburgh Panthers": "Pennsylvania",
    "Louisville Cardinals": "Kentucky",
    "Wake Forest Demon Deacons": "North Carolina",
    # ── NCAA — Pac-12 / 10 ───────────────────────────────────────────────────
    "Oregon Ducks": "Oregon",
    "Oregon State Beavers": "Oregon",
    "Washington Huskies": "Washington",
    "Washington State Cougars": "Washington",
    "Arizona Wildcats": "Arizona",
    "Arizona State Sun Devils": "Arizona",
    "UCLA Bruins": "California",
    "USC Trojans": "California",
    "California Golden Bears": "California",
    "Stanford Cardinal": "California",
    "Utah Utes": "Utah",
    "Colorado Buffaloes": "Colorado",
    # ── NCAA — other notable programs ─────────────────────────────────────────
    "Connecticut Huskies": "Connecticut",
    "UConn Huskies": "Connecticut",
    "Gonzaga Bulldogs": "Washington",
    "Memphis Tigers": "Tennessee",
    "Villanova Wildcats": "Pennsylvania",
    "BYU Cougars": "Utah",
    "Boise State Broncos": "Idaho",
    "Army Black Knights": "New York",
    "Navy Midshipmen": "Maryland",
    "Air Force Falcons": "Colorado",
    "New Mexico Lobos": "New Mexico",
    "Nevada Wolf Pack": "Nevada",
    "Hawaii Rainbow Warriors": "Hawaii",
    "Montana Grizzlies": "Montana",
    "North Dakota State Bison": "North Dakota",
    "Wyoming Cowboys": "Wyoming",
    "Creighton Bluejays": "Nebraska",
    "Rhode Island Rams": "Rhode Island",
    "Vermont Catamounts": "Vermont",
    "Delaware Fightin Blue Hens": "Delaware",
    "Maine Black Bears": "Maine",
    "New Hampshire Wildcats": "New Hampshire",
    "South Dakota Coyotes": "South Dakota",
    "Alaska Nanooks": "Alaska",
    # ── WNBA ─────────────────────────────────────────────────────────────────
    "Atlanta Dream": "Georgia",
    "Chicago Sky": "Illinois",
    "Connecticut Sun": "Connecticut",
    "Dallas Wings": "Texas",
    "Indiana Fever": "Indiana",
    "Las Vegas Aces": "Nevada",
    "Los Angeles Sparks": "California",
    "Minnesota Lynx": "Minnesota",
    "New York Liberty": "New York",
    "Phoenix Mercury": "Arizona",
    "Seattle Storm": "Washington",
    "Washington Mystics": "District of Columbia",
}

_PAREN_RE = re.compile(r'\(([^)]+)\)\s*$')
_YEAR_SUFFIX_RE = re.compile(r'\s*\(\d{4}[-–]\s*\d{0,4}\s*\)\s*$')


def glocation_to_state(gloc: str) -> str | None:
    gloc = gloc.strip()
    lower = gloc.lower()

    # Direct state name match (handles "California", "New York State", etc.)
    if lower in _STATE_NAMES:
        return _STATE_NAMES[lower]

    # Extract parenthetical abbreviation: "Chicago (Ill)" → "ill" → Illinois
    m = _PAREN_RE.search(gloc)
    if m:
        abbr = m.group(1).lower().rstrip('.')
        if abbr in _ABBR:
            return _ABBR[abbr]
        if abbr in _STATE_NAMES:
            return _STATE_NAMES[abbr]

    # Strip parenthetical and try city lookup: "Los Angeles" (after removing "(Calif)")
    city = _PAREN_RE.sub('', gloc).strip().lower()
    if city in _CITIES:
        return _CITIES[city]
    if city in _STATE_NAMES:
        return _STATE_NAMES[city]

    return None


def organizations_to_states(orgs: list[str]) -> list[str]:
    """Return unique states for any recognized team names in the organizations list."""
    seen: set[str] = set()
    result: list[str] = []
    for org in orgs:
        state = TEAM_STATE.get(org)
        if state and state not in seen:
            seen.add(state)
            result.append(state)
    return result


def clean_person_name(name: str) -> str:
    """Strip NYT birth-year suffix: 'Smith, John (1975- )' -> 'Smith, John'"""
    return _YEAR_SUFFIX_RE.sub('', name).strip()
