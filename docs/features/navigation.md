# Navigation

The top bar groups every page by what you are doing:

| Menu | Pages |
|---|---|
| **Hunt** | Explore, Hunts, Correlations |
| **Intel** | Indicators, Review queue, Source quality, Warninglists, Taxonomies, Galaxies |
| **Ingest** | Feeds, MISP servers, Alert webhooks |
| **Share** | Detection profiles, Exports, Sinks, External dynamic lists |
| **Tech lab** | Notebooks, Reactor scripts, Transformation servos, Enrichment modules |
| **Admin** | Users, Organisations, Roles, Runtime settings, API keys (admin), Audit logs, Tasks, Diagnostics |

Each menu lists its pages with an icon and a line on what each is for. The
menu of the page you are on is highlighted, and so is the page itself.

<img src="../../screenshots/navigation/misp-workbench-1_navigation_menu.png#only-light" alt="The Intel menu, open on the Indicators page" style="max-width: 100%; height: auto;">
<img src="../../screenshots/navigation/misp-workbench-1_navigation_menu-dark.png#only-dark" alt="The Intel menu, open on the Indicators page" style="max-width: 100%; height: auto;">

On the right are **+ New Event**, the theme switch, the notifications bell and
the **account menu**: your profile, your API keys, your user settings, and
sign out. Every page has one place: account pages are in the account menu
only, and notifications are behind the bell.

## What you see

Pages you can't open aren't shown, and a menu with none left isn't shown
either. Each page needs the scope its API needs: a read-only analyst sees
**Hunt** and **Intel**, an administrator sees everything. ***Admin*** →
***Roles*** shows which scopes each role grants.

The same scopes guard the pages themselves. A link to a page your role
doesn't open, such as a bookmark or a link shared by an administrator, shows
*No access to …* with the scope it needs, instead of a page whose every
request fails. Event, attribute and object pages are guarded by their own
API, not by Explore's scope.

## Quick switcher

<kbd>Ctrl</kbd>+<kbd>K</kbd> (<kbd>⌘</kbd>+<kbd>K</kbd> on a Mac), or **Search or jump to…** in the top bar,
opens the quick switcher:

- **A page:** type part of its name or what it's for (`warn`, `block lists`),
  then press <kbd>Enter</kbd>.
- **An event, attribute or object:** paste its uuid and the switcher looks it
  up, among those you may read.
- **A value:** an IP address, a domain or a hash offers *Search in Explore*
  and *Find indicators*.

<img src="../../screenshots/navigation/misp-workbench-2_navigation_quick-switcher.png#only-light" alt="The quick switcher" style="max-width: 640px; width: 100%; height: auto;">
<img src="../../screenshots/navigation/misp-workbench-2_navigation_quick-switcher-dark.png#only-dark" alt="The quick switcher" style="max-width: 640px; width: 100%; height: auto;">

## Keyboard

| Keys | Where | Does |
|---|---|---|
| <kbd>Tab</kbd> | top bar | moves between the menus |
| <kbd>Enter</kbd> or <kbd>Space</kbd> | a menu | opens it |
| <kbd>↓</kbd> <kbd>↑</kbd> | an open menu, the quick switcher | moves between entries |
| <kbd>Enter</kbd> | an entry | opens the page |
| <kbd>Esc</kbd> | an open menu, the quick switcher | closes it and returns focus |

## On a phone

The ☰ button opens the same menus as sections. The section of the page
you are on starts open, and every entry is a full-width target.

<img src="../../screenshots/navigation/misp-workbench-3_navigation_mobile.png#only-light" alt="The menu on a phone" style="max-width: 320px; width: 100%; height: auto;">
<img src="../../screenshots/navigation/misp-workbench-3_navigation_mobile-dark.png#only-dark" alt="The menu on a phone" style="max-width: 320px; width: 100%; height: auto;">

## Adding a page

The menus, the phone menu and the quick switcher are all built from one file,
`frontend/src/components/menu/menu.js`. A new page is one entry there: its
route, icon, one-line description and the scope it needs, which also guards
the route. Its unit tests
check that every route has a place in the menu and that no page appears
twice.
