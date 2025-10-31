# Organizing Reminders with Bins

##

Just thinking about bins and tags.

Processing bin paths seems ad hoc and likely to lead to poor organization and requires the use of a reminder to create the components of the path.

Given the uniqueness requirement for bin names, I'm wondering if it would be better to have "@b name" specify a given bin name, not path. A list of of possible completions could be offered as characters are entered, perhaps with something like tab completion for a unique match? For a new bin, the user could be prompted for a parent bin, again from a list of possible completions as characters are entered, perhaps with "unlinked" as the default?

For bin organization, what about a devoted, expanding tree view of just bins in which a bin could be selected by choosing its tag and, once selected, renamed or, after selecting the tag of a target, moved to the list of children of that target. Moving a bin with children would preserve the links and thus move the children as well. Also, a new bin could be created and attached to the list of children of an existing bin by selecting the tag of the target. Deleting a bin with children bins or reminders would require more thought.

If this could all be made sensible, what about using bins for tags. I.e., having a root/tags bin and when, e.g, "@t blue" encountered, automatically create "tag:blue" if it doesn't already exist and add it to the tags bin?

- activities
- journal
- library
- people
- places
- tags
- unlinked

# Bins

- activities
  - travel
    - Greece to Turkey Dec 2025
      - % itenerary @b activities/travel/Greece to Turkey Dec 2025 @b Smith, Charles and Bonnie
- ideas
- journal
  - 2025
    - 10
      - % ... @b journal/2025/2025:10
- library
- people
  - S
    - Smith, Charles and Bonnie
      - % ... @b people/people:S/Smith, John
- places
  - Greece
    - Greece to Turkey Dec 2025
  - Turkey
    - Greece to Turkey Dec 2025
- social:

  - wine societ ,y
  - chefs table

- Notes named "%y-%m-%d jots" with the reminder created for the date specified by @s

## backup

yesterday da - db
one week ago - two weeks ago db - dc  
two weeks ago - four weeks ago dc - dd
four-weeks ago - six weeks ago dd - de

- daily: 2025-10-25
  - tklr.db -> 2025-10-25.db

### One class

I have an idea for using a single Bin class to handle the display.
The view should show
a) the path to this bin, if not null ( root), as the header
b) the list of contained bins, if any, sorted alphabetically, with tags
c) the list of contained reminders, if any, with tags

Tags: The components of the path should be tagged starting with "a". E.g.,
"a: activities / b: travel" with the contained bins and reminders picking up
the tag sequence where the header left off.

Pages: When pages are necessary, the path heading should be repeated on subsequent
pages with "(continued)" appended.

Key presses: Pressing a key corresponding to a bin tag should switch the display
to that bin. This applies to the header tags as well as the bin tags. Pressing escape
should display the root bins. Pressing the tag for a reminder, should open the details
pane to display the details for the reminder.

Formatting: rows should be formatted differently for bins than for remainders.

Thoughts?

Component bins:
