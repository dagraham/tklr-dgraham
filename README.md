<table>
  <tr>
    <td style="vertical-align: top; width: 75%;">
      <h1>tklr</h1>
      <p>
        The term <em>tickler file</em> originally referred to a file system for reminders which used 12 monthly files and 31 daily files. <em>Tklr</em>, pronounced "tickler", is a digital version that ranks tasks by <i>urgency</i>, goals by <i>priority</i>, and generally facilitates the same purpose - managing what you need to know quickly and easily. It supports a wide variety of reminder types,  a simple, text-based entry format with timely, automatic assistance, the datetime parsing and recurrence features of <em>dateutil</em> and provides both command line (<i>Click</i>) and graphical (<i>Textual</i>) user interfaces.
      </p>
      <p>Make the most of your time!</p>
    </td>
    <td style="width: 25%; vertical-align: middle;">
      <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/tklr_logo.avif"
           alt="tklr logo" title="Tklr" style="max-width: 360px; width: 100%; height: auto;">
    </td>
  </tr>
</table>


This introduction to *tklr* is best viewed at [GitHub.io](https://dagraham.github.io/tklr-dgraham/) - *tklr* itself is available from [PyPi](https://pypi.org/project/tklr-dgraham/) and [GitHub](https://github.com/dagraham/tklr-dgraham) and further information at [Tklr Discussions](https://github.com/dagraham/tklr-dgraham/discussions).

<strong>This README is a work-in-progress. This notice will be removed when all the major sections have been completed.</strong>

<a id="table-of-contents"></a>
<details>
  <summary><strong>Table of Contents</strong></summary>
  <ul>
    <li>
      <details>
        <summary><a href="#1-what-makes-tklr-different">1. What makes <em>tklr</em> different</a></summary>
        <ul>
          <li><a href="#11-form-free-entry">1.1. Form-free entry</a></li>
          <li>
            <details>
              <summary><a href="#12-support-for-wide-variety-of-reminder-types-and-attributes">1.2. Support for wide variety of reminder types and attributes</a></summary>
              <ul>
                <li><a href="#121-an-event-lunch-with-ed-extended">1.2.1. An <em>event</em>: lunch with Ed (extended)</a></li>
                <li><a href="#122-a-task-pick-up-milk">1.2.2. A <em>task</em>: pick up milk</a></li>
                <li><a href="#123-a-repeating-event-trash-pickup">1.2.3. A <em>repeating event</em>: trash pickup</a></li>
                <li><a href="#124-an-event-that-repeats-irregularly-dental-appointment">1.2.4. An <em>event that repeats irregularly</em>: dental appointment</a></li>
                <li><a href="#125-a-complicated-but-regularly-repeating-task-vote-for-president">1.2.5. A <em>complicated</em> but regularly repeating task: vote for president</a></li>
                <li><a href="#126-an-offset-task-fill-bird-feeders">1.2.6. An <em>offset task</em>: fill bird feeders</a></li>
                <li><a href="#127-a-note-a-favorite-churchill-quotation">1.2.7. A <em>note</em>: a favorite Churchill quotation</a></li>
                <li><a href="#128-a-project-build-a-dog-house-with-component-tasks">1.2.8. A <em>project</em>: build a dog house with component tasks</a></li>
                <li><a href="#129-a-goal-interval-training-3-times-each-week">1.2.9. A <em>goal</em>: interval training 3 times each week</a></li>
                <li><a href="#1210-a-draft-reminder-meet-alex-for-coffee---time-to-be-determined">1.2.10. A <em>draft</em> reminder: meet Alex for coffee - time to be determined</a></li>
              </ul>
            </details>
          </li>
          <li><a href="#13-useful-attributes">1.3. Useful attributes</a></li>
        </ul>
      </details>
    </li>
    <li>
      <details>
        <summary><a href="#2-views">2. Views</a></summary>
        <ul>
          <li><a href="#21-agenda-view">2.1. Agenda View</a></li>
          <li><a href="#22-bins-view">2.2. Bins View</a></li>
          <li><a href="#23-completed-view---to-be-done">2.3. Completed View</a></li>
          <li><a href="#24-find-view">2.4. Find View</a></li>
          <li><a href="#25-goals-view">2.5. Goals View</a></li>
          <li><a href="#26-last-view">2.6. Last View</a></li>
          <li><a href="#27-modified-view---to-be-done">2.7. Modified View</a></li>
          <li><a href="#28-next-view">2.8. Next View</a></li>
          <li><a href="#29-query-view---to-be-done">2.9. Query View</a></li>
          <li><a href="#210-remaining-alerts-view---to-be-done">2.10. Remaining Alerts View</a></li>
          <li><a href="#211-tags-view---to-be-done">2.11. Tags View</a></li>
          <li><a href="#212-weeks-view">2.12. Weeks View</a></li>
        </ul>
      </details>
    </li>
  </ul>
</details>

## 1. What makes tklr different

### 1.1. Form-free entry

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-a.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
Rather than filling out fields in a form to create or edit reminders, a simple text-based format is used with <i>just in time prompting</i>.
  </p>
<p>
  Here a new reminder is being created. Below the entry area, the prompt indicates that the first step is to enter the type character for the reminder.
</p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-b.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
After the type character is entered, the prompt changes to indicate that the next step is to enter the subject of the reminder.
  </p>
<p>
  These prompts are displayed <i>just in time</i> to assist with the creation of the reminder. They do not interfere with the entry process in any way and will increasingly be ignored as familiarity is gained.
</p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-c.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
As the subject is entered, the prompt changes to reflect the current value of the entry.
  </p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-d.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
After the subject is entered, adding an <code>@</code> character changes the prompt to a list of the required and optional attributes which can still be entered.
  </p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-e.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
Entering an available key changes the prompt to a description of the attribute.
  </p>
  <p>
Here <code>@s</code>, has been selected and the prompt changes to show that this attibute, which is required for an event, specifies the scheduled datetime at which the event begins.
  </p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-f.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
<i>Fuzzy parsing</i> is supported for entering dates or datetimes in <i>tklr</i>. Since it was January 5, 2026 when this entry was made, the interpretation is that <code>12p</code> means 12:00pm on Jan 5.
  </p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-g.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
  Adding <code>fri</code> changes the interpretation to Friday of the current week.
  </p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-h.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
  Adding <code>@</code> again shows the current list of required and optional attributes, but this time with <code>@s</code> removed since it has already been entered.
  </p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-i.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
  Adding <code>e</code> changes the prompt to indicate that this attribute is used to specify the <i>extent</i> of the event, i.e., how long the event lasts.
  </p>
</div>
<div style="clear: both;"></div>


<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-j.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
  Adding <code>1h</code> specifies an <i>extent</i> of one hour. With this setting, the event would last from 12pm until 1pm.
  </p>
  <p> In addition to <code>h</code> for hours, other options include <code>m</code> for minutes, <code>d</code> for days and <code>w</code> for weeks. These can be combinded so that, e.g.,  <code>2h30m</code> would represent two hours and thirty minutes.
  </p>
</div>
<div style="clear: both;"></div>

↩︎ [Back to TOC](#table-of-contents)

### 1.2. Support for wide variety of reminder types and attributes

*tklr* has six item types, each with a corresponding type character:

| type    | character |
| ------- | --------- |
| event   | *         |
| task    | ~         |
| project | ^         |
| goal    | !         |
| note    | %         |
| draft   | ?         |

Here are some illustrations of how the various types and attributes can be put to use.

#### 1.2.1. An _event_: lunch with Ed (extended)

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>* lunch with Ed @s 12p fri @e 1h @a 30m: n
</code>
  </pre>
<p>The <code>*</code> makes this reminder an <i>event</i> with whatever follows up to the next <code>@</code> character as the subject. The <code>@s</code> attribute sets the <i>scheduled</i> or starting time for 12pm on the first Friday after today and the <code>@e 1h</code> attribute sets the <i>extent</i> for one hour. This event will thus be displayed as occupying the period <code>12-1pm</code> on that Friday. The distinguishing feature of an <i>event</i> is that it occurs at a particular time and the <code>@s</code> attribute is therefore required.
</p>
<p>If the <em>tklr ui</em> is running, the addition of <code>@a 30m: n</code> will trigger a built-in <em>notify</em> alert thirty minutes before the start of the event that sounds a bell and posts a message on the <em>tklr</em> display showing the subject and time of the event.
</p>
</div>
<div style="clear:both;"></div>

↩︎ [Back to TOC](#table-of-contents)

#### 1.2.2. A _task_: pick up milk

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>~ pick up milk
</code>
  </pre>
  <p>The beginning <code>~</code> type character makes this reminder a <i>task</i> with the following <code>pick up milk</code> as the <i>subject</i>.
  </p>

  <p>Using an <code>@s</code> attribute is optional and, when specified, it sets the time at which the task should be <em>completed</em>, not begun. The <code>@e</code> attribute is also optional and, when given, is intepreted as the estimated time period required for completion.
  </p>
</div>
<div style="clear:both;"></div>

↩︎ [Back to TOC](#table-of-contents)

#### 1.2.3. A _repeating event_: trash pickup

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>* trash pickup @s 8a mon @n 1d @r w &w MO
</code>
  </pre>
<p>This <em>event</em> repeats because of the <code>@r w &w MO</code> each week on Mondays. Because of the <code>@n 1d</code> a notice will be posted in <em>Agenda View</em> when the current date is within one day of the scheduled datetime or, in this case, on Sundays. This serves as a reminder to put the trash at the curb before 8am Mondays. Why not use a <em>task</em> for this? A task would require being marked finished each week to avoid accumulating past due instances - even when out of town with neither trash nor opportunity for placement at the curb.
</p>
</div>
<div style="clear:both;"></div>

↩︎ [Back to TOC](#table-of-contents)

#### 1.2.4. An _event that repeats irregularly_: dental appointment

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>* dental exam and cleaning
  @s 2p feb 5
  @e 45m
  @+ 9am Sep 3
</code>
  </pre>
<p>This event specifies an appointment for a 45 minute dental exam and cleaning starting at 2pm on February 5 and then again, because of the <code>@+</code> attribute, at 9am on September 3.
</p>

<p>Need to add another datetime to an existing reminder? Just add an <code>@+</code> attribute with a comma separated list of as many additional dates or datetimes as needed.
</p>
</div>
<div style="clear:both;"></div>

↩︎ [Back to TOC](#table-of-contents)

#### 1.2.5. A _complicated_ but regularly repeating task: vote for president

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>~ vote for president
  @s nov 1 2020
  @r y &i 4 &w TU &d 2, 3, 4, 5, 6, 7, 8 &m 11
</code>
  </pre>
  <p>Here is another, more complicated, but still <em>regularly repeating</em> reminder. Beginning with November, 2020, this <em>task</em> repeats every 4 years on the first Tuesday after a Monday in November (a <em>Tuesday</em> whose <em>month day</em> falls between 2 and 8 in the 11th <em>month</em>).
  </p>

  <p>This is a good illustration of the power of the <em>dateutil</em> library. Note that the only role of <code>@s nov 1 2020</code> is to limit the repetitions generated by <code>@r</code> to those falling on or after November 1, 2020 and occur on that year or a multiple of 4 years after that year.
  </p>
</div>
<div style="clear:both;"></div>


↩︎ [Back to TOC](#table-of-contents)

#### 1.2.6. An _offset task_: fill bird feeders

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>~ fill birdfeeders @s 3p sat @n 1d @o 12d
</code>
  </pre>
<p>Because of the <code>@o 12d</code> <em>offset</em> attribute, when this task is completed the <code>@s</code> <em>scheduled</em> datetime will automatically reset to the datetime that falls precisely 12 days after the completion datetime. Whether they are filled early or late, they will still need to be refilled 12 days after they were last filled.  Because of the <code>@n 1d</code> <em>notice</em> attribute, this task will <em>not</em> appear in the <em>Agenda View</em> task list until the the current datetime is within one day of the <em>scheduled</em> datetime.
</p>
</div>
<div style="clear:both;"></div>

Since the <code>@o</code> attribute involves resetting attibutes  in a way that effectively repeats the <em>task</em>:

1. `@o` can only be used with _tasks_
2. Using `@o` precludes the use of `@r`


It is worth noting the different roles of two attributes in events and tasks.

1. The <em>scheduled</em> datetime attribute describes when an event begins but when a task should be completed.
2. The <em>notice</em> attribute provides an early warning for an event but postpones the disclosure of a task.

↩︎ [Back to TOC](#table-of-contents)

#### 1.2.7. A _note_: a favorite Churchill quotation

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>% Give me a pig - #Churchill
  @d Dogs look up at you.
  Cats look down at you.
  Give me a pig - they look you in the eye
    and treat you as an equal.
  @b quotations
</code>
  </pre>
  <p>The beginning <code>%</code> makes this reminder a <i>note</i> with the <i>subject</i>, <code>Give me a pig - #Churchill</code>. The optional <i>details</i> attribute follows the <code>@d</code> and is meant to be more expansive - analogous to the body of an email. The hash character that precedes 'Churchill' in the subject makes that word a <i>hash tag</i> for listing in <i>Tags View</i>. The <code>@b</code> entry adds this reminder to the 'quotations' <i>bin</i> for listing in <i>Bins View</i>.
  </p>
</div>
<div style="clear:both;"></div>


↩︎ [Back to TOC](#table-of-contents)

#### 1.2.8. A _project_: build a dog house with component tasks

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>^ Build dog house
  @~ pick up materials &r 1 &e 4h
  @~ cut pieces &r 2: 1 &e 3h
  @~ assemble &r 3: 2 &e 2h
  @~ sand &r 4: 3 &e 1h
  @~ paint &r 5: 4 &e 4h
</code>
  </pre>
      <p>The beginning <code>^</code> makes this a <i>project</i>. This is a collection of related tasks specified by the <code>@~</code> entries. In each task, the <code>&r X: Y</code> <em>requires</em> attribute sets <code>X</code> as the label for the task and sets the task labeled <code>Y</code> as a requirement or prerequisite for <code>X</code>. E.g., <code>&r 3: 2</code> establishes "3" as the label for assemble and "2" (cut pieces) as a prerequisite. The <code>&e</code> <i>extent</i> entries give estimates of the times required to complete the various tasks.
      </p>
    </div>
<div style="clear:both;"></div>

↩︎ [Back to TOC](#table-of-contents)

#### 1.2.9. A _goal_: interval training 3 times each week

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>! interval training @s 2026-01-05 @o 3/1w
</code>
  </pre>
  <p>The beginning <code>!</code> type character makes this reminder a <i>goal</i> with the following <code>interval training</code> as the <i>subject</i>. The <code>@t 3/1w</code> attribute is required and sets the <i>target</i> to be 3 completions during the period of one week starting at midnight on '2026-01-05', because of the <code>@s</code> attribute, and ending one week later at midnight on '2026-01-12', because of the '1w' target period.
  </p>
</div>
<div style="clear:both;"></div>

When a *goal* is created, the attribute `@k 0` is automatically added to indicate that the current *completion count* is zero. When a completion is recorded for the *goal*, this count is automatically increased by one. This process continues until

1. the period allowed for completing the goal expires or
2. the completion count reaches the target number of completions

In either case, `@k` is reset to zero and `@s` is reset to the previous value *plus* the period allowed for completion of the goal, i.e, to the *end* of the period originally allowed for completion.

↩︎ [Back to TOC](#table-of-contents)

#### 1.2.10. A _draft_ reminder: meet Alex for coffee - time to be determined

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>? Coffee with Alex @s fri @e 1h
</code>
  </pre>
  <p>The beginning <code>?</code> type character makes this a <i>draft</i> reminder. This can be changed to an event when the details are confirmed by replacing the <cold>?</code> with an <code>*</code> and adding the time to <code>@s fri</code>.
  </p>
  <p>
  This is a reminder that is not yet finished and, in almost every respect, will be ignored by <em>tklr</em>. The exception is that it will appear highlighted on the current day in <em>Agenda View</em> until it is revised. It can be changed to an <em>event</em> when the details are confirmed by replacing the <code>?</code> with an <code>*</code> and adding the time to <code>@s</code>.
  </p>
</div>
<div style="clear:both;"></div>

↩︎ [Back to TOC](#table-of-contents)

### 1.3. Useful attributes

- {XXX} anniversary substitutions
- @m



## 2. Views

  Each of the views listed below can be opened by entering the first letter of the view's name, e.g., pressing `A` (`shift+a`) will open _Agenda View_.

  These views involve vertical lists of reminders, each row beginning with a tag from "a", "b", ..., "z", followed by the pertinent details of the reminder. When necessary, lists are split into pages so that no more than 26 reminders appear on any one page. The left and right cursor keys are used to move back and forth between pages.

  On any page, pressing the key corresponding to a tag will open a display with all the details of the corresponding reminder. When the details of reminder are being displayed, various commands are available to modify the reminder. Press `enter` to display a menu of the available options and `enter` again with an option selected to use it or `escape` to close the menu.   Additionally, the key corresponding to the tag of another reminder will switch the details display to that reminder, `escape` will close the details display and entering the upper case letter corresponding to another view will open that view.

  The point of using tags to select and display reminders in this way is to minimize key presses. Any reminder on a page can be selected and its details displayed with a single key press.

↩︎ [Back to TOC](#table-of-contents)

  ### 2.1. Agenda View

  The next three days of _events_ together with _notices_ and _drafts_ followed by goals ordered by priority and then tasks ordered by urgency.

The first day will always include any _notice_ or _drafts_ in addition to any scheduled events. In this case the reminber tagged _b_ indicates that there is an event beginning in 4 days (`+4d`) whose subject begins with "Quisquam" and which has a _notice_ entry, "@n INTERVAL" in which `INTERVAL > 4d`. This notice of the upcoming event will be displayed on the first day (current date) of Agenda View each day until the day of the event.

There is also a draft entry displayed in red. This is simply a reminder whose item type is "?". This is used to flag a reminder as incomplete as would be the case, e.g., if a final datetime for the event had not yet been finalized. Draft reminders are displayed on the current, first day in Agenda view until the item type is changed.

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/events_1_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Agenda View: Upcoming events and tasks ordered by urgency</em>
</p>

Since there are more than 26 reminders to be displayed and only 26 available lower-case letters to use as tags, the reminders are spread over as many pages as necessary with _left_ and _right_ cursor keys to change pages. Here is the second page.

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/events_2_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Agenda View: The second and last page</em>
</p>

↩︎ [Back to TOC](#table-of-contents)

### 2.2. Bins View

Hierarchical display of bins and reminders.

Many note taking applications provide a means for establishing links between notes. The terms _Zettelkasten_ and _Second Brain_ come to mind. A different approach is taken in _tklr_ where _bins_ serve as containers for both reminders and other bins. While a system of links between reminders might be broken by the removal of a reminder, when a reminder is removed from _tklr_, it simply disappears from the relevant bin membership lists. Bins themselves and their membership lists are otherwise unaffected.

These are the important facts:

1. Bin names are unique.
2. A bin can contain **many** other bins (children)
3. A bin can belong to **at most one** other bin (parent).
4. A reminder can belong to **many** bins.

The first three are illustrated by _Bins_ view:

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/bin_root_screenshot.svg"
       alt="Bins: root is the active parent" width="540">
  <br>
  <em>Bins: root is the active parent</em>
</p>

You may think in the _journal_ branch the years _2025_, _2026_ and so forth may be unique, but surely the months _11_, _12_, and so forth, will be repeated. Similarly, under _people_, the children names _A_, _B_, ... might be needed for other purposes as well. How is uniqueness to be maintained? The solution is that _11_, _12_, _A_, _B_, ... are aliases for the actual bin names which are, in fact, _2025:11_, _2025:12_, _people:A_, _people:B_, .... The general rule is this: whenever a bin named _XXX:YYY_ is the child of a bin named _XXX_, the child will be displayed using the alias _YYY_. Why this insistence upon uniqueness? It means that specifying membership in the bin _root / journal / 2025 / 2025:11_ can be done by just specifying `@b 2025:11`.

As an illustration of the power of being able to place a reminder in many bins consider a note describing a visit to Lille, France on November 11, 2025 which involved meeting a dear friend, Mary Smith for lunch. Bins to which this might belong:

- _travel_ (in _activities_)
- _2025:11_ (in _journal_)
- _Smith,Mary_ (in _people_)
- _Lille_ (in _places_)

As with the other views, key presses corresponding to _tags_ control the action. Note that the children of _root_ are tagged. Pressing the tag for _journal_, _b_, makes it the active parent:

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/bin_journal_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Bins: journal is the active parent</em>
</p>

Note the _bread crumb_ header, `0 root / journal`, in which _root_ now has the tag _0_ and is followed by _journal_ which is now the active parent with its children now displayed with tags. Pressing _0_ would restore _root_ as the active parent and pressing the tag for one of the children would make that the active parent. Here's the view that results from pressing _a_, the tag for _2025_:

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/bin_2025_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Bins: 2025 is the active parent</em>
</p>

Pressing _a_ again, now the tag for _2025:11_, makes this the active parent:

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/bin_202511_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Bins: 2025 is the active parent</em>
</p>

Notice in the _bread crumb_ header that there are integer tags going backward for each of the ancestors and the active parent is, as usual, the last element of the path. But it is listed here not using the alias, _11_, but the actual bin name, _2025:11_.

↩︎ [Back to TOC](#table-of-contents)

### 2.3. Completed View - TO BE DONE

↩︎ [Back to TOC](#table-of-contents)

### 2.4. Find View

Reminders whose subject or detail entries contain a case-insensitive match for an entered expression.

When you need an exhaustive search across all reminders for a case-insensitive match in either the subject or the details, this is the view. Just press "F" in any view to activate the search bar:

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/find_entry_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Find: initializing the search</em>
</p>

When submitted, the matching reminders are listed:

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/find_matches_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Find: matching reminders</em>
</p>

↩︎ [Back to TOC](#table-of-contents)

### 2.5. Goals View

Press `G` to open Goal View displaying a tagged list of *goals* sorted by their *priority*.

How is *priority* calculated?  Suppose, for example, `@t 3/1w` is specified in a goal, then `n = 3` is the specified number of completions and `t = 1w` is the time period allowed for their completion. Further suppose that at a particular moment, `n'` is the number of instances remaining unfinished and `t'` is the time remaining in the period for their completion.  Initially, the needed rate of completions to satisfy the goal is `n/t`. At the moment being considered, the needed rate of completions goal is `n'/t'`.

Now consider these possibilities:

- ` n'/t' > n/t `:
    the needed completion rate has increased  - completions are behind schedule
- ` n'/t' = n/t `:
    the needed completion rate is unchanged - completions are on schedule
- ` n'/t' < n/t `:
    the needed completion rate has decreased - completions are ahead of schedule

If *priority* is defined the current rate of completion as a percentage of the original rate,  `100 (n' / t') / (n / t) = 100 (n' t) / (t' n)`, then these possibilites can be restated as

- `priority > 100`:
    the needed completion rate has increased  - completions are behind schedule
- `priority = 100`:
    the needed completion rate is unchanged - completions are on schedule
- `priority < 100`:
    the needed completion rate has decreased - completions are ahead of schedule


Consider a goal a goal with the target `@t n/t` so that `n` is the number of completions intended for the period `t`, `n'` the number of instances remaining this period, and `t'` the time remaining before the period ends. The ratio `priority = 100 * (n' * t) / (n * t')` indicates how far ahead or behind the schedule you are:

- `priority > 100`: the goal is behind schedule, so it floats to the top of the view.
- `priority = 100`: you are on schedule.
- `priority < 100`: you are ahead of schedule.

The time remaining column uses the current datetime, so refreshing the view immediately reflects newly completed instances.

- 00:00-05:59 _night_
- 06:00-11:59 _morning_
- 12:00-17:59 _afternoon_
- 18:00-23:59 _evening_

If the busy period for an event overlaps one or more of these periods then those periods are tentatively colored green. If the busy periods for two events overlap within one or more periods, then those periods are colored red to indicate the conflict. E.g., the red _afternoon_ cell for Wednesday, reflects the conflict between the reminders tagged _g_ and _h_

Pressing _g_ displays the details for that reminder.

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/week_with_details_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Weeks View: details for the reminder tagged g</em>
</p>

↩︎ [Back to TOC](#table-of-contents)

### 2.6. Last View

The last instance of every scheduled reminder occurring before the current moment listed in **descending** order by date and time.

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/last_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Agenda View: The second and last page</em>
</p>

↩︎ [Back to TOC](#table-of-contents)

### 2.7. Modified View - TO BE DONE

↩︎ [Back to TOC](#table-of-contents)

### 2.8. Next View

The first instance of every scheduled reminder occurring after the current moment listed in **ascending** order by date and time.

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/next_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Agenda View: The second and last page</em>
</p>

Need to find, say, your next dental appointment - this is the view. Just press _/_ to activate search and enter the expression.

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/search_entry_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Search: initializing the search</em>
</p>

The reminders with case-insensitive matches will be highlighted:

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/search_matching_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Search: highlighted matches</em>
</p>

↩︎ [Back to TOC](#table-of-contents)

### 2.9. Query View - TO BE DONE

↩︎ [Back to TOC](#table-of-contents)

### 2.10. Remaining Alerts View - TO BE DONE

↩︎ [Back to TOC](#table-of-contents)

### 2.11. Tags View - TO BE DONE

↩︎ [Back to TOC](#table-of-contents)

### 2.12. Weeks View

Scheduled Reminders for the Week with busy times displayed by a leading _busy bar_.

<p align="center">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/week_screenshot.svg"
       alt="Agenda view in Tklr" width="540">
  <br>
  <em>Weeks View: busy bar and scheduled reminders for week</em>
</p>

The _left_ and _right_ cursor keys shift the display backward and forward one week at a time. Adding _shift_ to these cursor keys shifts by four weeks at a time. The _space_ key restores the display to the current week.

There are 5 cells in the _busy bar_ for each week day. The first (furthest left) displays a yellow square if an _all day event_ such as a holiday is scheduled for that date. The remaining 4 cells correspond to the 6-hour periods during the day:

↩︎ [Back to TOC](#table-of-contents)

## Details

### DateTime details

Intelligent parsing of the user's entry of a datetime is supported. Suppose it is Thursday, November 6 2025 in the US/Eastern timezone. When a datetime is entered it is interpreted _relative_ to the current date, time and timezone. When entering the scheduled datetime for a reminder using `@s`, the following table illustrates how various entries would be interpreted and the resulting user feedback.

| @s entry        | interpretation       | user feedback              |
| --------------- | -------------------- | -------------------------- |
| wed             | 2025-11-12           | Wed, Nov 12 2025           |
| 9a              | 2025-11-06 09:00 EST | Thu, Nov 6 2025 09:00 EST  |
| 9a fri          | 2025-11-07 09:00 EST | Fri, Nov 7 2025 09:00 EST  |
| 10 9p z none    | 2025-11-10 09:00     | Mon, Nov 10 2025 21:00     |
| 3p z US/Pacific | 2025-11-06 18:00 EST | Thu, Nov 6 2025 18:00 EST  |
| 10 13:30 z CET  | 2025-11-10 07:30 EST | Mon, Nov 10 2025 07:30 EST |
| 10 20h z none   | 2025-11-23 20:00     | Mon, Nov 10 2025 20:00     |

Datetimes entered with "z none" and dates are _naive_ - have no timezone information. Datetimes entered with "z TIMEZONE" are interpreted as _aware_ datetimes in TIMEZONE. Datetimes without a "z" entry are also interpreted as _aware_ but in the timezone of the user's computer. Aware datetimes are always reported using the timezone of the user's computer, wherever it might be. Times can be entered using the suffix of either a/p or am/pm for AM/PM times or h for 24-hour times. Times are reported using the preference of the user, here as 24-hour times.

Why would you want to use a "z" in specifying a time? Suppose a colleague in Europe at asked you to call Friday at 18:00 CET time. Then setting "@s fri 18h z CET" will schedule your reminder for the correct time to call wherever you might be. In the US/Eastern timezone, this would be "Fri, Nov 12 2025 12:00 EST". As a second example, suppose you want to take a daily medication at 4pm in whatever timezone you happen to be. Then you will want to schedule the reminder for "@s 4p z none".

When dates and datetimes are recorded, _aware_ datetimes are first converted to UTC time and then stored with a "Z" appended. E.g., the "3p z US/Pacific" datetime would be interpreted as "2025-11-06 18:00 EST" but would be recorded as "20251106T2300Z". Dates and _naive_ datetimes are recorded without conversion and without the trailing "Z". When _aware_ datetimes are displayed to the user, they are first converted to the timezone of the user's computer. Thus the "PST" example would be displayed as scheduled for 6pm today in US/Eastern. Dates and _naive_ datetimes are displayed without change in every timezone.

When an `@s` scheduled entry specifies a date without a time, i.e., a date instead of a datetime, the interpretation is that the task is due sometime on that day. Specifically, it is not due until `00:00` on that day and not past due until `00:00` on the following day. The interpretation of `@b` and `@u` in this circumstance is similar. For example, if `@s 2025-04-06` is specified with `@b 3d` and `@u 2d` then the task status would change from waiting to pending at `2025-04-03 00:00` and, if not completed, to deleted at `2025-04-09 00:00`.

Note that times can only be specified, stored and displayed in hours and minutes - seconds and microseconds are not supported. Internally datetimes are interpreted as having seconds equal to 0.

### Interval details

An interval is just a period of time and is entered in _tklr_ using expressions such as

| entry | period of time          |
| ----- | ----------------------- |
| 2h    | 2 hours                 |
| -2h   | - 2 hours               |
| 1w7d  | 1 week and 7 days       |
| 2h30m | 2 hours and 30 minutes  |
| 1m27s | 1 minute and 27 seconds |

Note that w (weeks), d (days), h (hours), m (minutes) and s (seconds) are the available _units_ for entering _intervals_. Seconds are ignored save for their use in alerts - more on alerts later.

An interval, `I`, can be added to a datetime, `T`, to get a datetime, `T + I`, that will be after `T` if `I > 0` and before `T` if `I < 0`. Similarly, one datetime, `A`, can be subtracted from another, `B`, to get an interval, `I = B - A`, with `I > 0` if `B` is after (greater than) `A` and `I < 0` if `B` is before (less than) `A`.

### Scheduled datetime details

For the discussion that follows, it will be assumed that the current date is `2025-10-01` and that the _scheduled datetime_ for the illustrative reminder is

    @s 2025-10-21 10:00am

#### extent

The entry `@e 2h30m` would set the _extent_ for the reminder to two hours and 30 minutes.

If the reminder were an _event_, this would schedule the "busy time" for the event to _extend_ from 10am until 12:30pm.

For a task, this same entry would indicate that attention to completing the task should begin no later than 10am and that 2 hours and 30 minutes is the _estimate_ of the time required for completion. The period from 10am until 12:30pm is not displayed as a busy time, however, since the task could be begun before or after 10am and could take more or less than 2 hours and 30 minutes to complete. For a task, both `@s` and `@e` are best regarded as _estimates_.

For a project, this same entry would similarly indicate that attention to completing the project should begin no later than 10am and that two hours and 30 minutes is estimated for completion subject to additional times specified in the jobs. A job entry containing `&s 2d &e 3h`, for example, would set the scheduled time for this job to be two days _after_ the `@s` entry for the project and would add three hours to the estimate of total time required for the project.

#### notice

The entry `@n I` where `I` is a _positive_ interval specifies that a notice for the reminder should begin on the date in which `scheduled - I` falls. For the example, adding `@b 1d12h` would set _notice_ to the date corresponding to

      2025-10-21 10am - 1d12h = 2025-10-19 10pm

so notices would begin on `2025-10-19`.

If the reminder is an event, then the agenda view would display an notice for the event beginning on `25-10-19` and continuing on the `25-10-20`, i.e., from the date of the notice through the date before the scheduled datetime. For an _event_ think of this notice as a visual alert of the proximity of the event.

If the reminder is a task, then the task would _not_ appear in the agenda view until `25-10-19`, i.e., it would be hidden before that date.

#### wrap

The entry `@w BEFORE, AFTER`, where `BEFORE` and `AFTER` are _intervals_, can be used to wrap the _scheduled_ datetime of a reminder. Possible entries and the resulting values of BEFORE and AFTER are illustrated below:

| entry      | before | after      |
| ---------- | ------ | ---------- |
| @w 1h, 30m | 1 hour | 30 minutes |
| @w 1h,     | 1 hour | None       |
| @w , 30m   | None   | 30 minutes |

Consider an event with `@s 2025-10-21 10am @e 2h30m`, which starts at 10am and ends at 12:30pm and suppose that it will take an hour to travel to the location of the event and 30 minutes to travel from the event to the next location. The entry `@w 1h, 30m` could be used to indicate these travel periods from 9am until 10am before the event begins and from 12:30pm until 1pm after the event ends.

#### alert

An alert is specified using `@a <list of invervals> : <list of commands>`. An `@s <datetime>` is required and the result is to execute the commands in `<list of commands>` at the datetimes resulting from subtracting the intervals in `<list of intervals>` from `<datetime>`. E.g., with `@s 17:00 fri` and `@a 1h, -15m: c, d`, the commands `c` and `d` would each be executed at `17:00 - 1h = 16:00` and `17:00 + 15m = 17:15` on Friday.

A command such as `d` in the example must be specified in the user configuration file. This is the relevant section:

```
[alerts]
# dict[str, str]: character -> command_str.
# E.g., this entry
#   d: '/usr/bin/say -v Alex "[[volm 0.5]] {subject}, {when}"'
# would, on my macbook, invoke the system voice to speak the subject
# of the reminder and the time remaining until the scheduled datetime.
# The character "d" would be associated with this command so that, e.g.,
# the alert entry "@a 30m, 15m: d" would trigger this command 30
# minutes before and again 15 minutes before the scheduled datetime.
```

### Recurrence details

#### @r and, by requirement, @s are given

When an item is specified with an `@r` entry, an `@s` entry is required and is used as the `DTSTART` entry in the recurrence rule. E.g.,

```
* datetime repeating @s 2025-11-06 14:00 @r d &i 2
```

With this entry, the `@s 2025-11-06 14:00` and `@r d &i 2` parts would be combined by _tklr_ to generate this _rruleset_:

```
      "rruleset": "DTSTART:20251106T1900Z\nRRULE:FREQ=DAILY;INTERVAL=2"
```

Two aspects of this _rruleset_ are worth emphasizing

1. "DTSTART:20251106T1900Z\nRRULE:FREQ=DAILY;INTERVAL=2" is a string and can therefore be stored without conversion in SQLite3 - the database used for _tklr_.
2. Even though it is only 50 characters long, it actually represents an infinite number of datetimes - every datetime matching the recurrence rule which occurs on or after 2025-11-06 19:00 UTC.

In the hands of the wonderful _python_ library _dateutil_, this _rruleset_ string can be asked a variety of useful questions which will be answered almost instantly. E.g, What datetimes does it represent which lie between 2025-06-23 08:00 and 2026-01-01 00:00?, What is the first datetime after 2025-10-15 00:00? What is the last datetime before 2025-12-15 00:00? And so forth.

**For every reminder in tklr which involves datetimes, a rruleset is used to represent all of those datetimes.**

**Note**: The datetimes generated by the _rruleset_ correspond to datetimes matching the specification of `@r` which occur **on or after** the datetime specified by `@s`. The datetime corresponding to `@s` itself will only be generated if it matches the specification of `@r`.

#### @s is given but not @r

On the other hand, if an `@s` entry is specified, but `@r` is not, then the `@s` entry would be stored as an `RDATE` in the recurrence rule. E.g.,

```python
* datetime only @s 2025-11-06 14:00
```

would be serialized (stored) as

```
  "rruleset": "RDATE:20251106T1900Z"
```

The datetime corresponding to `@s` itself is, of course, generated in this case.

#### @+ is specified, with or without @r

When `@s` is specified, an `@+` entry can be used to specify one or more, comma separated datetimes. When `@r` is given, these datetimes are added to those generated by the `@r` specification. Otherwise, they are added to the datetime specified by `@s`. E.g., is a special case. It is used to specify a datetime that is relative to the current datetime. E.g.,

```
   ... @s 2025-11-06 14:00 @+ 2025-11-13 21:00
```

would be serialized (stored) as

```
  "rruleset": "RDATE:20251106T1900Z, 20251114T0200Z"
```

This option is particularly useful for irregular recurrences such as annual doctor visits. After the initial visit, subsequent visits can simply be added to the `@+` entry of the existing event once the new appointment is made.

**Note**: Without `@r`, the `@s` datetime is included in the datetimes generated but with `@r`, it is only used to set the beginning of the recurrence and otherwise ignored.

### Timezone considerations

When a datetime is specified without an `z` component, the timezone is assumed to be aware and in the local timezone. The datetime is converted to UTC for storage in the database. When a datetime is displayed, it is displayed using the local timezone of the computer.

This remains true with _recurrence_ and _daylight savings time_ but is a little more complicated. As always, the recurrence rules are stored in UTC and the datetimes generated by the rules are also in UTC. When these datetimes are displayed, they are converted to the local timezone.

```
   ... @s 2025-10-31 14:00 @r d &i 1 &c 4
```

With this entry, the rruleset and datetimes generated show the effect of the transition from daylight to standard time:

```
"rruleset": "DTSTART:20251031T1800Z\nRRULE:FREQ=DAILY;INTERVAL=1;COUNT=4"

  Fri 2025-10-31 14:00 EDT -0400
  Sat 2025-11-01 14:00 EDT -0400
  Sun 2025-11-02 13:00 EST -0500
  Mon 2025-11-03 13:00 EST -0500
```

### Urgency

Since urgency values are used ultimately to give an ordinal ranking of tasks, all that matters is the relative values used to compute the urgency scores. Accordingly, all urgency scores are constrained to fall within the interval from -1.0 to 1.0. The default urgency is 0.0 for a task with no urgency components.

There are some situations in which a task will _not_ be displayed in the "urgency list" and there is no need, therefore, to compute its urgency:

- Completed tasks are not displayed.
- Hidden tasks are not displayed. The task is hidden if it has an `@s` entry and an `@b` entry and the date corresponding to `@s - @b` falls sometime after the current date.
- Waiting tasks are not displayed. A task is waiting if it belongs to a project and has unfinished prerequisites.
- Only the first _unfinished_ instance of a repeating task is displayed. Subsequent instances are not displayed.

There is one other circumstance in which urgency need not be computed. When the _pinned_ status of the task is toggled on in the user interface, the task is treated as if the computed urgency were equal to `1.0` without any actual computations.

All other tasks will be displayed and ordered by their computed urgency scores. Many of these computations involve datetimes and/or intervals and it is necessary to understand both are represented by integer numbers of seconds - datetimes by the integer number of seconds _since the epoch_ (1970-01-01 00:00:00 UTC) and intervals by the integer numbers of seconds it spans. E.g., for the datetime "2025-01-01 00:00 UTC" this would be `1735689600` and for the interval "1w" this would be the number of seconds in 1 week, `7*24*60*60 = 604800`. This means that an interval can be subtracted from a datetime to obtain another datetime which is "interval" earlier or added to get a datetime "interval" later. One datetime can also be subtracted from another to get the "interval" between the two, with the sign indicating whether the first is later (positive) or earlier (negative). (Adding datetimes, on the other hand, is meaningless.)

Briefly, here is the essence of this method used to compute the urgency scores using "due" as an example. Here is the relevant section from config.toml with the default values:

```toml
[urgency.due]
# The "due" urgency increases from 0.0 to "max" as now passes from
# due - interval to due.
interval = "1w"
max = 8.0
```

The "due" urgency of a task with an `@s` entry is computed from _now_ (the current datetime), _due_ (the datetime specified by `@s`) and the _interval_ and _max_ settings from _urgency.due_. The computation returns:

- `0.0`
  if `now < due - interval`
- `max * (1.0 - (now - due) / interval)`
  if `due - interval < now <= due`
- `max`
  if `now > due`

For a task without an `@s` entry, the "due" urgency is 0.0.

Other contributions of the task to urgency are computed similarly. Depending on the configuration settings and the characteristics of the task, the value can be either positive or negative or 0.0 when missing the requisite characteristic(s).

Once all the contributions of a task have been computed, they are aggregated into a single urgency value in the following way. The process begins by setting the initial values of variables `Wn = 1.0` and `Wp = 1.0`. Then for each of the urgency contributions, `v`, the value is added to `Wp` if `v > 0` or `abs(v)` is added to `Wn` if `v` negative. Thus either `Wp` or `Wn` is increased by each addition unless `v = 0`. When each contribution has been added, the urgency value of the task is computed as follows:

```python
urgency = (Wp - Wn) / (Wp + Wn)
```

Equivalently, urgency can be regarded as a weighted average of `-1.0` and `1.0` with `Wn/(Wn + Wp)` and `Wp/(Wn + Wp)` as the weights:

```python
urgency = -1.0 * Wn / (Wn + Wp) + 1.0 * Wp / (Wn + Wp) = (Wp - Wn) / (Wn + Wp)
```

Observations from the weighted average perspective and the fact that `Wn >= 1` and `Wp >= 1`:

- `-1.0 < urgency < 1`
- `urgency = 0.0` if and only if `Wn = Wp`
- `urgency` is _always increasing_ in `Wp` and _always decreasing_ in `Wn`
- `urgency` approaches `1.0` as `Wn/Wp` approaches `0.0` - as `Wp` increases relative to `Wn`
- `urgency` approaches `-1.0` as `Wp/Wn` approaches `0.0` - as `Wn` increases relative to `Wp`

Thus positive contributions _always_ increase urgency and negative contributions _always_ decrease urgency. The fact that the urgency derived from contributions is always less than `1.0` means that _pinned_ tasks with `urgency = 1` will always be listed first.

## Getting Started

### Developer Install Guide

This guide walks you through setting up a development environment for `tklr` using [`uv`](https://github.com/astral-sh/uv) and a local virtual environment. Eventually the normal python installation procedures using pip or pipx will be available.

#### ✅ Step 1: Clone the repository

This step will create a directory named _tklr-dgrham_ in your current working directory that contains a clone of the github repository for _tklr_.

```bash
git clone https://github.com/dagraham/tklr-dgraham.git
cd tklr-dgraham
```

#### ✅ Step 2: Install uv (if needed)

```bash
which uv || curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### ✅ Step 3: Create a virtual environment with `uv`

This will create a `.venv/` directory inside your project to hold all the relevant imports.

```bash
uv venv
```

#### ✅ Step 4: Install the project in editable mode

```bash
uv pip install -e .
```

#### ✅ Step 5: Use the CLI

You have two options for activating the virtual environment for the CLI:

##### ☑️ Option 1: Manual activation (every session)

```bash
source .venv/bin/activate
```

Then you can run:

```bash
tklr --version
tklr add "- test task @s 2025-08-01"
tklr ui
```

To deactivate:

```bash
deactivate
```

##### ☑️ Option 2: Automatic activation with `direnv` (recommended)

###### 1. Install `direnv`

```bash
brew install direnv        # macOS
sudo apt install direnv    # Ubuntu/Debian
```

###### 2. Add the shell hook to your `~/.zshrc` or `~/.bashrc`

```sh
eval "$(direnv hook zsh)"   # or bash
```

Restart your shell or run `source ~/.zshrc`.

###### 3. In the project directory, create a `.envrc` file

```bash
echo 'export PATH="$PWD/.venv/bin:$PATH"' > .envrc
```

###### 4. Allow it

```bash
direnv allow
```

Now every time you `cd` into the project, your environment is activated automatically and, as with the manual option, test your setup with

```bash
tklr --version
tklr add "- test task @s 2025-08-01"
tklr ui
```

You're now ready to develop, test, and run `tklr` locally with full CLI and UI support.

#### ✅ Step 6: Updating your repository

To update your local copy of **Tklr** to the latest version:

```bash
# Navigate to your project directory
cd ~/Projects/tklr-dgraham  # adjust this path as needed

# Pull the latest changes from GitHub
git pull origin master

# Reinstall in editable mode (picks up new code and dependencies)
uv pip install -e .
```

### Starting tklr for the first time

**Tklr** needs a _home_ directory to store its files - most importantly these two:

- _config.toml_: An editable file that holds user configuration settings
- _tkrl.db_: An _SQLite3_ database file that holds all the records for events, tasks and other reminders created when using _tklr_

Any directory can be used for _home_. These are the options:

1. If started using the command `tklr --home <path_to_home>` and the directory `<path_to_home>` exists then _tklr_ will use this directory and, if necessary, create the files `config.toml` and `tklr.db` in this directory.
2. If the `--home <path_to_home>` is not passed to _tklr_ then the _home_ will be selected in this order:

   - If the current working directory contains files named `config.toml` and `tklr.db` then it will be used as _home_
   - Else if the environmental variable `TKLR_HOME` is set and specifies a path to an existing directory then it will be used as _home_
   - Else if the environmental variable `XDG_CONFIG_HOME` is set, and specifies a path to an existing directory which contains a directory named `tklr`, then that directory will be used.
   - Else the directory `~/.config/tklr` will be used.

### Configuration

The default settings are in _config.toml_ in your _tklr_ home directory together with detailed explanations for each setting.
