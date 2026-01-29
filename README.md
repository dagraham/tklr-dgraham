<!-- markdownlint-disable MD033 -->
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

The [↩︎](#table-of-contents) links at the end of major sections lead back to this **expandable** *Table of Contents*.

<a id="table-of-contents"></a>
<details>
  <summary><strong>Table of Contents</strong></summary>
  <ul>
    <li>
      <details>
        <summary><a href="#1-what-makes-tklr-different">1. What makes <em>tklr</em> different</a></summary>
        <ul>
          <li><a href="#11-form-free-entry">1.1. Form-Free entry</a></li>
          <li><a href="#12-reminders-to-suit-the-purpose">1.2. Reminders to suit the purpose</a></li>
          <li><a href="#13-mouse-free-navigation">1.3. Mouse-Free navigation</a></li>
          <li><a href="#14-agenda-view-your-daily-brief">1.4. Agenda View: Your daily brief</a></li>
          <li><a href="#15-weeks-next-and-last-views-whats-happening-and-when">1.5. Weeks, Next and Last Views: What's happening and when</a></li>
          <li><a href="#16-bins-and-tags-views-organizing-your-reminders">1.6. Bins and Tags Views: Organizing your reminders</a></li>
          <li><a href="#17-query-and-find-views-wheres-waldo">1.7 Query and Find Views: Where's Waldo</a></li>
          <li><a href="#18-sqlite3-data-store">1.8 SQLite3 Data Store</a></li>
        </ul>
      </details>
      <details>
        <summary><a href="#2-details">2. Details</a></summary>
        <ul>
          <li><a href="#21-datetimes">2.1. Datetimes</a></li>
          <li><a href="#22-timedeltas">2.2. TimeDeltas</a></li>
          <li><a href="#23-scheduled-datetime">2.3. Scheduled datetime</a></li>
          <li><a href="#24-extent-timedelta">2.4. Extent timedelta</a></li>
          <li><a href="#25-notice">2.5. Notice</a></li>
          <li><a href="#26-wrap">2.6. Wrap</a></li>
          <li><a href="#27-alert">2.7. Alert</a></li>
          <li><a href="#28-recurrence">2.8. Recurrence</a></li>
          <li><a href="#29-anniversaries">2.9. Anniversaries</a></li>
          <li><a href="#210-timezones">2.10. Timezones</a></li>
          <li><a href="#211-urgency">2.11. Urgency</a></li>
          <li><a href="#212-priority">2.12. Priority</a></li>
          <li><a href="#213-masked-information">2.13. Masked Information</a></li>
          <li><a href="#214-open-with-default">2.14. Open with default</a></li>
          <li><a href="#215-away-from-your-computer-use-the-cloud">2.15. Away from your computer? Use the cloud</a></li>
        </ul>
      </details>
      <details>
        <summary><a href="#3-getting-started">3. Getting Started</a></summary>
      </details>
      <details>
        <summary><a href="#4-using-the-command-line-interface">4. Using the Command Line Interface</a></summary>
      </details>
      <details>
        <summary><a href="#5-coming-from-etm">5. Coming from <em>etm</em></a></summary>
      </details>
      <details>
        <summary><a href="#6-developer-guide">6. Developer Guide</a></summary>
      </details>
    </li>
  </ul>
</details>


## 1. What makes tklr different

### 1.1. Form-Free entry

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-a.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
Rather than filling out fields in a form to create or edit reminders, a simple entry field is provided for text input together with a prompt area which provides <i>instantaneous feedback</i>.
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
  The prompt is updated <i>as the entry changes</i> to assist with the editing of the reminder. This does not interfere with the entry process but, like the speedometer in a car, ensures that the relevant information is there if wanted.
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
<i>Fuzzy parsing</i> is supported for entering dates or datetimes in <i>tklr</i>. Since it was January 26, 2026 when this entry was made, the interpretation is that <code>12p</code> means 12:00pm on Jan 26.
  </p>
</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/new_event-g.svg" alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>
  Adding <code>fri</code> changes the interpretation to Friday of this week.
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

[↩︎](#table-of-contents)

### 1.2. Reminders to suit the purpose

*tklr* has six types of reminders, each with a corresponding type character:

| item type | character |
| --------- | :-------: |
| event     |     *     |
| task      |     ~     |
| project   |     ^     |
| goal      |     !     |
| note      |     %     |
| draft     |     ?     |

Here are some illustrations of how the various types and attributes can be put to use.

<a id="reminder-types"></a>

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

#### 1.2.1. An _event_: lunch with Ed (extended)

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>* lunch with Ed
  @s 12p fri @e 1h
  @a 30m: n
</code>
  </pre>
<p>The <code>*</code> makes this reminder an <i>event</i> with whatever follows until the next <code>@</code> character as the subject. The <code>@s</code> attribute sets the <i>scheduled</i> or starting time for 12pm on the first Friday after today and the <code>@e 1h</code> attribute sets the <i>extent</i> for one hour. This event will thus be displayed as occupying the period <code>12-1pm</code> on that Friday. The distinguishing feature of an <i>event</i> is that it occurs at a particular time and the <code>@s</code> attribute is therefore required.
</p>
<p>Provided that <em>tklr ui</em> is running, <code>@a 30m: n</code> will trigger a built-in <em>notify</em> alert thirty minutes before the start of the event which sounds a bell and posts a message on the <em>tklr</em> display showing the subject and time of the event.
</p>
</div>
<div style="clear:both;"></div>


#### 1.2.2. A _task_: pick up milk

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>~ pick up milk
</code>
  </pre>
  <p>The beginning <code>~</code> type character makes this reminder a <i>task</i> with the following <code>pick up milk</code> as the <i>subject</i>.
  </p>

  <p>Using an <code>@s</code> attribute is optional and, when specified, it sets the time at which the task should be <strong>completed</strong>, not begun. The <code>@e</code> attribute is also optional and, when given, is intepreted as the estimated time period required for completion.
  </p>
</div>
<div style="clear:both;"></div>


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



<a id="doghouse-example"></a>

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


#### 1.2.10. A _draft_ reminder: meet Alex for coffee - time to be determined

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>? Coffee with Alex @s fri @e 1h
</code>
  </pre>
  <p>The beginning <code>?</code> type character makes this a <i>draft</i> reminder. This can be changed to an event when the details are confirmed by replacing the <code>?</code> with an <code>*</code> and adding the time to <code>@s fri</code>.
  </p>
  <p>
  This is a reminder that is not yet finished and, in almost every respect, will be ignored by <em>tklr</em>. The exception is that it will appear highlighted on the current day in <em>Agenda View</em> until it is revised. It can be changed to an <em>event</em> when the details are confirmed by replacing the <code>?</code> with an <code>*</code> and adding the time to <code>@s</code>.
  </p>
</div>
<div style="clear:both;"></div>


[↩︎](#table-of-contents)

### 1.3. Mouse-Free navigation

Each of the main views in *tklr* can be opened by pressing a single key - the first letter of the view's name.

| View      |  Key  | Displays                                       |
| --------- | :---: | ---------------------------------------------- |
| Agenda    |   A   | events, goals, tasks                           |
| Bins      |   B   | Tree view of Bins                              |
| Completed |   C   | Completion datetimes for completed tasks       |
| Find      |   F   | Case insenstive search in subjects and details |
| Last      |   L   | The last instance of reminders before today    |
| Modified  |   M   | All reminders sorted by the modified timestamp |
| Next      |   N   | The next instance of reminders after today     |
| Query     |   Q   | List matches for a specified query             |
| Remaining |   R   | List remaining alerts for the today            |
| Tags      |   T   | List reminders with tags grouped by tag        |
| Weeks     |   W   | List scheduled reminders by week and weekday   |


Each of these views displays a vertical list of reminders, with each reminder row beginning with a tag from "a", "b", ..., "z", followed by the pertinent details of the reminder including its subject.  When necessary, lists are split into pages so that no more than 26 reminders appear on any one page and the left and right cursor keys are used to move back and forth between pages.

*The view keys and the list tags are the key to navigating tklr.*

On any page, pressing the key corresponding to a tag will open a display with all the details of the corresponding reminder. This is worth emphasizing. *You don't need the cursor keys or the mouse to select a reminder - just press the key corresponding to its tag.*

When the details of reminder are being displayed, pressing `enter` will open a menu of various commands applicable to the selected reminder, pressing the key corresponding to the tag of another reminder will switch the details display to that reminder or pressing the upper case letter corresponding to another view will switch to that view.

Everything you might want to do to a reminder, to edit, finish, reschedule, delete or whatever is available using these steps:

1. press the key corresponding to the tag of the reminder you want to select
2. press `enter` to open the menu of commands for the selected reminder
3. press the first letter (any case) of the desired command or `escape` to cancel and close the commands menu

[↩︎](#table-of-contents)

### 1.4. Agenda View: Your daily brief

*Agenda view* displays

1. The next few days of <em>events</em> beginning with today
2. Active <em>goals</em> ordered by their *priority*
3. Available <em>tasks</em> ordered by their *urgency*

Times are displayed in the screenshots using _24-hour_ notation. An option can be set to display times using _am/pm_ notation instead.

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/agenda_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>While the listing of events begins with the current day, any all-day events or events whose ending times have already passed such as the one tagged <em>a</em> will be dimmed. Additionally an event, such as the one tagged <em>b</em> whose active period overlaps the current moment will be highlighted.
  </p>
  <p>The first day of events will always include any <em>notices</em> of upcomming events or <em>draft</em> reminders needing completion in addition to any scheduled events for today. In this case the reminder tagged <em>d</em> indicates that there is an event beginning in 5 days (<code>+5d</code>) with a subject beginning with "Amet porro ..." and a <em>notice attribute</em>, <code>@n x</code>, in which <code>x > 5d</code>. This attribute is the reason this notice of the event is being displayed before its scheduled datetime - it will continue to be displayed on the first day (current date) of Agenda View each day until the day of the event.
  </p>
    <p>There is also a draft entry tagged <em>e</em> and displayed in red. This is simply a reminder whose item type is <code>?</code>. This is used to flag a reminder as incomplete as would be the case, e.g., if a final datetime for the event had not yet been finalized. Draft reminders are also displayed on the current, first day in Agenda view until the item type is changed.
    </p>
    <p>The list for *goals* includes all goals which have not been completed on the current date, sorted and color coded by their *priorty*, which is listed in the first column after the tags. The details for precisely how *priority* is calculated will be described later but the basic idea involves comparing</p>

  <ol>
    <li>the rate at which completions would currently need to occur to complete the goal</li>
    <li>the rate originally specified in the goal</li>
  </ol>

  <p>The higher the current rate relative to the original, the higher the *priority*.</p>

  <p>The list for *tasks* includes all tasks with the possible exception of tasks with both an `@s` (specifying a *due datetime*) and an `@n` entry (specifying a *notification period*).  Suppose, for example, that `@s 2026-01-30` and `@n 2d`. The role of these combined entries is to say that the task needs to be finished by `2026-01-30` but you don't want to be bothered about it until two days before that date. This task won't appear in the list until `2026-01-28`.</p>

  <p>Tasks are sorted by their *urgency*. This calculation is fairly complicated and will be described later. Many factors are involved including the priority of the task, its due datetime, how many tags it has, whether it has a details attribute and so forth. The *weights* attached to these and other characteristics are options which can be set in the user configuration file.</p>

  <p>*Agenda* is the default view and represents the place to go for what you need to know right now.</p>

</div>
<div style="clear: both;"></div>


[↩︎](#table-of-contents)

### 1.5 Weeks, Next and Last Views: What's happening and when

*Weeks View* is dedicated to displaying each instance of your scheduled reminders one week at a time with a *busy bar* at the top to show the busy days during the week at a glance followed by a day by day listing of the scheduled reminders.

Two supporting views are limited to displaying a single instance of each scheduled reminder. *Next View*, bound to <code>N</code>, lists the *first* instance occurring on or after the current date in *ascending* order and *Last View*, bound to <code>L</code>, lists the most recent instance occurring *before* the current date in *descending* order. When did you last have your car serviced? *Last View* is the place to look. When is your next dental appointment? *Next View* has the answer.

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/weeks_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">

  <p>Press <code>W</code> to open <em>Weeks View</em> on the current week or press <code>J</code> and enter a date to open the view on the week containing that date. The header displays the date range, year and week number for the displayed week. Left and right cursor keys shift the displayed week backward or forward by one week. Pressing the shift key at the same time increases the shift from one to four weeks. Pressing the space key will jump back to the current week.
 </p>

  <p>As with the other tagged views, pressing the key corresponding to the tag of a reminder opens a panel with the details of that reminder. In this case, the details for tag <em>j</em> are being displayed.
  </p>

  <p> The <em>busy bar</em> underneath the header provides graphical illustration of the busy times for <em>events</em> during the week. The area under each weekday name has spaces for five blocks. The first (furthest to the left) will be colored orange if one or more <em>all day</em> events are scheduled for that day. The next four blocks correspond to the four 6-hour periods during the day beginning with 00:00 - 05:59 and ending with 18:00 - 23:59 - night, morning, afternoon and evening.
  </p>
  <p>The block corresponding to a period will be green if the scheduled time for an event occupies any part of the period. E.g., a single event scheduled for 05:00 - 07:00 would cause both the first and second blocks for that day to be colored green. A block is changed from green to red if the busy periods for two or more events overlap and thus <em>conflict</em>. The red block for Tuesday, e.g., reflects the conflict during the period 11:00 - 11:15 by the events tagged <em>b</em> and <em>c</em>.
  </p>

  <p>Note that only <em>events</em> with an <em>extent</em> contribute to the <em>busy bar</em>. E.g., the <em>event</em> tagged <em>i</em> on Friday has no extent and thus no effect on the <em>busy bar</em> "morning" slot for that day. Similarly, the <em>task</em> tagged <em>j</em> whose details are displayed, is scheduled for 10:15 - 11:15 and yet, being a task, also has no effect on that "morning" slot.
  </p>

</div>
<div style="clear: both;"></div>

[↩︎](#table-of-contents)

### 1.6. Bins and Tags Views: Organizing your reminders

*Tklr* provides two complementary methods for organizing your reminders:

<ol>
  <li>Using the attribute <code>@b</code> to attach the the name of a bin to a reminder and the related <em>Bins View</em></li>
  <li>Using a <em>hash tag</em>, i.e., <code>&#x23;</code> followed without spaces by an arbitrary word, in either the <em>subject</em> or the <em>details</em> attribute of reminders and the related <em>Tags View</em></li>
</ol>


#### 1.6.1 Bins View

The _Bins View_ displays a hierarchical, tree view of _bins_ and _reminders_.

Think of _bins_ as directories, _reminders_ as files and _Bin View_ as a file browser. The main difference is that _reminders_ can belong to more than one _bin_ or to none at all.

As an illustration of the power of being able to place a reminder in many bins consider a note describing a visit to Lille, France on November 11, 2025 which involved meeting a dear friend, Mary Smith for lunch. This note might belong to all of these bins:

- _travel_ (in _activities_)
- _2025:11_ (in _journal_)
- _Mary Smith_ (in _people:S_)
- _Lille_ (in _places:France_)

Many note taking applications provide a means for establishing links between notes. The terms _Zettelkasten_ and _Second Brain_ come to mind. A different approach is taken in _tklr_ where _bins_ serve as containers for both reminders and other bins. While a system of links between reminders might be broken by the removal of a reminder, when a reminder is removed from _tklr_, it simply disappears from the relevant bin membership lists. Bins themselves and their membership lists are otherwise unaffected.

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/bin_root_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">

  <p>These are the important facts about <em>Bins</em>:
  </p>

  <ul>
    <li>Bin names are unique</li>
    <li>A bin can contain many other bins (children)</li>
    <li>A bin can belong to at most one other bin (parent)</li>
    <li>A reminder can belong to one or more bins by adding an <code>@b NAME</code> attribute with a unique <em>NAME</em> for each</li>
  </ul>

  <p>This is the opening, root level in <em>Bins view</em>.
  </p>
</div>

<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/bin_library_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">

  <p>Press <em>c</em> to open the <em>library</em> bin with its tagged list of children which now includes both bins and reminders.
  </p>

  <ul>
    <li>Use the tag for a bin to open the bin </li>
    <li>Use the tag for a reminder to display the details of the reminder</li>
    <li>Use tag <em>0</em>, <em>root</em>,in the <em>bread crumb trail</em> to go up to that bin</li>
  </ul>
</div>
<div style="clear: both;"></div>


<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/bin_quotations_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">

  <p>Press <em>e</em> to open the <em>quotations</em> bin with its tagged list of children which now includes only reminders.
  </p>
  <ul>
    <li>Use the tag for a reminder to display the details of the reminder</li>
    <li>Use tag <em>1</em>, <em>library</em>, in the <em>bread crumb trail</em> to go up to that bin</li>
    <li>Use tag <em>0</em>, <em>root</em>, in the <em>bread crumb trail</em> to go up to that bin</li>
  </ul>

</div>
<div style="clear: both;"></div>


[↩︎](#table-of-contents)


#### 1.6.2 Tags View

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/tags_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">

  <p>Press <em>T</em> to open the <em>Tags View</em> which lists reminders with <em>hash tag</em> entries grouped by the <em>tag name</em>.
  </p>

</div>
<div style="clear: both;"></div>

[↩︎](#table-of-contents)


### 1.7 Query and Find Views: Where's Waldo

What is the name of that plumber we used and liked so much?

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/query_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>Just press <code>Q</code> to open the <em>Query View</em>, enter your query at the prompt and press <code>Enter</code>.
  </p>
  <p>This query asks for reminders that <em>include</em> in their <em>subject</em> or their <em>details</em> a match for <em>plumber</em> and found one matching reminder.
  </p>
  <p>The key corresponding to the tag, <code>a</code>, was pressed to display the details of the match.  Note that <em>Plumber</em> is in the details and was matched despite being capitalized.
  </p>

</div>
<div style="clear: both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/query_exists_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>Here the query asks for reminders that pass the <em>exists</em> test for the attribute <em>r</em>, i.e., for all reminders with an <code>@r</code> attribute.
  </p>
</div>
<div style="clear: both;"></div>


<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/query_help_screenshot.svg"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>Press <code>?</code> to display the <em>help</em> information for <em>queries</em>.
  </p>
</div>
<div style="clear: both;"></div>


<p><em>Find View</em>. Looking for a case-insensitive match for a word in either the <em>subject</em> or the <em>details</em> of a reminder is such a common need that <em>tklr</em> provides a short-cut for this query - <em>Find View</em>. Instead of pressing <code>Q</code> and entering
</p>
<pre>includes subject d plumber</pre>
<p>you can instead press <code>F</code> to open the prompt for <em>Find View</em> and just enter the word being sought
</p>
<pre>plumber</pre>

### 1.8. <em>SQLite3</em> Data Store

SQLite offers tangible advantages over TinyDB’s JSON store which - used for *tklr*'s predecessor - especially at the required scale. The embedded SQL engine keeps queries fast even as data grows, thanks to indexed storage and compiled query plans rather than repeatedly parsing whole JSON file. Reliability improves because SQLite wraps writes in ACID transactions so crashes or concurrent edits won’t corrupt the data, whereas TinyDB depends on rewriting the JSON blob. Finally, SQLite’s standard file format means other tools (command-line clients, BI dashboards, scripting languages) can open the same .db directly or even run read-only analytics in parallel, something that’s awkward with a bespoke JSON structure.

[↩︎](#table-of-contents)

## 2. Details

### 2.1. DateTimes

Intelligent parsing of the user's entry of a datetime is supported. Suppose it is Thursday, November 6 2025 in the US/Eastern timezone. When a datetime is entered it is interpreted _relative_ to the current date, time and timezone. When entering the scheduled datetime for a reminder using `@s`, the following table illustrates how various entries would be interpreted and the resulting user feedback.

| @s entry        | interpretation       | user feedback              |
| --------------- | -------------------- | -------------------------- |
| wed             | 2025-11-12           | Wed, Nov 12 2025           |
| 9a              | 2025-11-06 09:00 EST | Thu, Nov 6 2025 09:00 EST  |
| 9a fri          | 2025-11-07 09:00 EST | Fri, Nov 7 2025 09:00 EST  |
| 10 9p z none    | 2025-11-10 21:00     | Mon, Nov 10 2025 21:00     |
| 3p z US/Pacific | 2025-11-06 18:00 EST | Thu, Nov 6 2025 18:00 EST  |
| 10 13:30 z CET  | 2025-11-10 07:30 EST | Mon, Nov 10 2025 07:30 EST |
| 10 20h z none   | 2025-11-23 20:00     | Mon, Nov 10 2025 20:00     |

Datetimes entered with "z none" and dates are _naive_ - have no timezone information. Datetimes entered with "z TIMEZONE" are interpreted as _aware_ datetimes in TIMEZONE. Datetimes without a "z" entry are also interpreted as _aware_ but in the timezone of the user's computer. Aware datetimes are always reported using the timezone of the user's computer, wherever it might be. Times can be entered using the suffix of either a/p or am/pm for AM/PM times or h for 24-hour times. Times are reported using the preference of the user, here as 24-hour times.

Why would you want to use a "z" in specifying a time? Suppose a colleague in Europe at asked you to call Friday at 18:00 CET time. Then setting "@s fri 18h z CET" will schedule your reminder for the correct time to call wherever you might be. In the US/Eastern timezone, this would be "Fri, Nov 12 2025 12:00 EST". As a second example, suppose you want to take a daily medication at 4pm in whatever timezone you happen to be. Then you will want to schedule the reminder for "@s 4p z none".

When dates and datetimes are recorded, _aware_ datetimes are first converted to UTC time and then stored with a "Z" appended. E.g., the "3p z US/Pacific" datetime would be interpreted as "2025-11-06 18:00 EST" but would be recorded as "20251106T2300Z". Dates and _naive_ datetimes are recorded without conversion and without the trailing "Z". When _aware_ datetimes are displayed to the user, they are first converted to the timezone of the user's computer. Thus the "PST" example would be displayed as scheduled for 6pm today in US/Eastern. Dates and _naive_ datetimes are displayed without change in every timezone.

When an `@s` scheduled entry specifies a date without a time, i.e., a date instead of a datetime, the interpretation is that the task is due sometime on that day. Specifically, it is not due until `00:00` on that day and not past due until `00:00` on the following day. The interpretation of `@b` and `@u` in this circumstance is similar. For example, if `@s 2025-04-06` is specified with `@b 3d` and `@u 2d` then the task status would change from waiting to pending at `2025-04-03 00:00` and, if not completed, to deleted at `2025-04-09 00:00`.

Note that times can only be specified, stored and displayed in hours and minutes - seconds and microseconds are not supported. Internally datetimes are interpreted as having seconds equal to 0.

[↩︎](#table-of-contents)

### 2.2. TimeDeltas

An <em>timedelta</em> is just a period of time and is entered in _tklr_ using expressions such as

| entry | period of time          |
| ----- | ----------------------- |
| 2h    | 2 hours                 |
| -2h   | - 2 hours               |
| 1w7d  | 1 week and 7 days       |
| 2h30m | 2 hours and 30 minutes  |
| 1m27s | 1 minute and 27 seconds |

Note that w (weeks), d (days), h (hours), m (minutes) and s (seconds) are the available _units_ for entering _intervals_. Seconds are ignored save for their use in alerts - more on alerts later.

<em>Arithmetic</em>. A timedelta, `D`, can be added to a datetime, `T`, to get a datetime, `T + D`, that will be after `T` if `D > 0` and before `T` if `D < 0`. Similarly, one datetime, `A`, can be subtracted from another, `B`, to get a timedelta, `T = B - A`, with `T > 0` if `B` is after (greater than) `A` and `T < 0` if `B` is before (less than) `A`.

One example of this arithmetic is that an event with `@s 10a fri @e 1h30m` will span the period <em>10:00 - 11:30</em> on Friday, the ending datetime corresponding to the sum of the <em>scheduled</em> datetime and the <em>extent</em> timedelta.

[↩︎](#table-of-contents)

### 2.3. Scheduled datetime

For the discussion that follows, it will be assumed that the current date is `2025-10-01` and that the _scheduled datetime_ for the illustrative reminder is

    @s 2025-10-21 10:00am

[↩︎](#table-of-contents)

### 2.4. Extent timedelta

The entry `@e 2h30m` would set the _extent_ for the reminder to two hours and 30 minutes.

If the reminder were an _event_, this would schedule the "busy time" for the event to _extend_ from 10am until 12:30pm.

For a task, this same entry would indicate that attention to completing the task should begin no later than 10am and that 2 hours and 30 minutes is the _estimate_ of the time required for completion. The period from 10am until 12:30pm is not displayed as a busy time, however, since the task could be begun before or after 10am and could take more or less than 2 hours and 30 minutes to complete. For a task, both `@s` and `@e` are best regarded as _estimates_.

For a project, this same entry would similarly indicate that attention to completing the project should begin no later than 10am and that two hours and 30 minutes is estimated for completion subject to additional times specified in the jobs. A job entry containing `&s 2d &e 3h`, for example, would set the scheduled time for this job to be two days _after_ the `@s` entry for the project and would add three hours to the estimate of total time required for the project.

[↩︎](#table-of-contents)

### 2.5. Notice timedelta

The entry `@n XYZ` where `XYZ` is a _positive_ timedelta specifies that a notice for the reminder should begin to be *noticed* on the date in which `scheduled - XYZ` falls. For the example, adding `@n 1d12h` would cause the reminder to be *noticed* beginning on

      2025-10-21 10am - 1d12h = 2025-10-19 10pm

If the reminder is an event, then the agenda view would display an notice for the event beginning on `25-10-19` and continuing on the `25-10-20`, i.e., from the date of the notice through the date before the scheduled datetime. For an _event_ think of this notice as a visual alert of the proximity of the event.

If the reminder is a task, then the task would _not_ appear in the agenda view until `25-10-19`, i.e., it would be hidden before that date.

[↩︎](#table-of-contents)

### 2.6. Wrap

The entry `@w BEFORE, AFTER`, where `BEFORE` and `AFTER` are _timedeltas_, can be used to wrap the _scheduled_ datetime of a reminder. Possible entries and the resulting values of BEFORE and AFTER are illustrated below:

| wrap       | before | after      |
| ---------- | ------ | ---------- |
| @w 1h, 30m | 1 hour | 30 minutes |
| @w 1h,     | 1 hour | None       |
| @w , 30m   | None   | 30 minutes |

Consider an event with `@s 2025-10-21 10am @e 2h30m`, which starts at 10am and ends at 12:30pm and suppose that it will take an hour to travel to the location of the event and 30 minutes to travel from the event to the next location. The entry `@w 1h, 30m` could be used to indicate these travel periods from 9am until 10am before the event begins and from 12:30pm until 1pm after the event ends. The event will be displayed with its actual starting and ending times but the entire period including the <em>wrap</em> will be treated as <em>busy</em>.

[↩︎](#table-of-contents)

### 2.7. Alert

An alert is specified using `@a <list of invervals> : <list of commands>`. An `@s <datetime>` is required and the result is to execute the commands in `<list of commands>` at the datetimes resulting from subtracting the intervals in `<list of intervals>` from `<datetime>`. E.g., with `@s 17:00 fri` and `@a 1h, -15m: n, v`, the commands `n` and `v` would each be executed at `17:00 - 1h = 16:00` and `17:00 + 15m = 17:15` on Friday.

The command `n` in the example is *built into tklr* - it sounds a bell and pops up a message on the *tklr* display which lasts for a minute (or until clicked on).  Other commands such as `v` in the example must be specified in the user configuration file. This is the relevant section:

```
[alerts]
# dict[str, str]: character -> command_str.
# E.g., this entry
#   v: '/usr/bin/say -v Alex "[[volm 0.5]] {subject}, {when}"'
# would, on my macbook, invoke the system voice to speak the subject
# of the reminder and the time remaining until the scheduled datetime.
# The character "v" would be associated with this command so that, e.g.,
# the alert entry "@a 30m, 15m: v" would trigger this command 30
# minutes before and again 15 minutes before the scheduled datetime.
```

[↩︎](#table-of-contents)

### 2.8. Recurrence

#### 2.8.1. When @r and, by requirement, @s are given

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

**Note**: The datetimes generated by the _rruleset_ correspond to datetimes matching the specification of `@r` which occur **on or after** the datetime specified by `@s`. **The datetime corresponding to `@s` itself will only be generated if it matches one of the instances generated by** `@r`.

#### 2.8.2. When @s is given but not @r

On the other hand, if an `@s` entry is specified, but `@r` is not, then the `@s` entry would be stored as an `RDATE` in the recurrence rule. E.g.,

```python
* datetime only @s 2025-11-06 14:00
```

would be serialized (stored) as

```
  "rruleset": "RDATE:20251106T1900Z"
```

The datetime corresponding to `@s` itself is, of course, generated in this case.

#### 2.8.3. When @+ is specified, with or without @r

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

#### 2.9. Anniversaries

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>* Max's {XXX} birthday
  @s 2016-10-23
  @r y &m 10 &d 23
</code>
  </pre>
  <p>Reminders that repeat using an <code>@r</code> attribute can automatically display the number of the anniversary. The <em>anniversary expression</em>, <code>{XXX}</code>, when placed in the <em>subject</em> will be replaced in the listing of the reminder in Agenda, Next and Weeks views by the relevant number of the anniversary. For example, in the listing for October 23, 2026, the subject of this reminder would appear as <code>Max's 10th birthday</code>. Note that the appropriate suffix from [st, nd, rd or th] is automatically applied and, because of the yearly frequency specified by <code>@r y</code>, the count represents the number of years separating the instance from the <em>scheduled</em> datetime.
  </p>
</div>
<div style="clear:both;"></div>


[↩︎](#table-of-contents)

### 2.10. Timezones

When a datetime is specified without an `z` component, the timezone is assumed to be aware and represented using the local timezone. The datetime is converted to UTC for storage in the database. When an awared datetime is displayed, it is displayed using the local timezone of the computer.

Suppose you're in the US/Eastern timezone and want to schedule a call to a friend at 3:00pm Friday, US/Pacific time. This could be entered as `@s 3p fri z US/Pacific`. This datetime would first be converted to UTC time and then stored as a string in the SQLite3 database. It would then be displayed to you in the local timezone of your computer, where ever it might be.

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

[↩︎](#table-of-contents)

### 2.11. Urgency

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

[↩︎](#table-of-contents)

### 2.12. Priority

How is *priority* calculated for *goals*?  Consider a goal a goal with the target `@t n/t` so that `n` is the number of completions intended for the period `t`. Suppose further that `n'` is the number of instances remaining to be completed this period and that `t'` is the time remaining in the period for their completion.

Now consider these possibilities:

- `n'/t' > n/t`:
    the needed completion rate has increased - completions are *behind* schedule
- `n'/t' = n/t`:
    the needed completion rate is unchanged - completions are *on* schedule
- `n'/t' < n/t`:
    the needed completion rate has decreased - completions are *ahead* of schedule

If <em>priority</em> is defined by ratio
```
  priority = 100 * (n' * t) / (n * t')
```
then it indicates the completion rate currently needed as a percentage of the original rate and the possibilities can be stated as:

- `priority > 100`: behind schedule.
- `priority = 100`: on schedule.
- `priority < 100`: ahead of schedule.

[↩︎](#table-of-contents)

### 2.13. Masked Information

A <code>@m</code> attribute can be used to record information in a reminder that will be stored in an obfuscated format. Only someone running *tklr* with the *secret* from the configuration file used to create the entry will see the clear value. Useful for passwords, account numbers, diary entries or whatever.

For example, this entry:
<pre>@m This is a masked entry - it should be readable in the details view of the UI but otherwise obfuscated.</pre>
would be displayed in the SQLite3 database as
<pre>{
    "token": "@m
    wrnClsOSwprDmMKKwrrDnGTDiGTCpsK0w5_CnMOPwq9twr3DlMOEwrXDjMKDecKNw4_Dq
    HHCqcOgw4jCp8Kuw45Rw4fDj3HDm8Kpw4jCqMKawrXDmMKWworCtMK7eMOawrjCqHPDh8
    Kxw6HDh8Odwr3CqcKYw4_Cm8Knw6FRw5TDkHHDncKsw4xkwo7CnMKMwpPDn8K_bcOHw5r
    CuMKow4XDmsK1w6DDi8KUw4DCmMOew47CpcKlw4vCpcOKw45_
    "t": "@",
    "k": "m",
    "masked": true
}</pre>

[↩︎](#table-of-contents)

### 2.14. Open with default

A <code>@g</code> attribute can be used to enter a URL, file or whatever which can the be "opened" using your system default application by selecting the item and using the menu command "Open with default". Example entries:

- URL: <code>@g https://dagraham.github.io/tklr-dgraham/</code>
  Open the URL in the default browser.
- Mail: <code>@g mailto:dnlgrhm@gmail.com</code>
  Open a new email to the provided address using the default email agent.
- File: <code>@g ~/Projects/tklr-uv/README.md</code>
  Open the markdown file using the system default agent for markdown files. (<em>Marked 2</em>?)
- File: <code>@g ~/Projects/tklr-uv/make_items.py</code>
  Open the python file using the system default agent for <code>.py</code> files. (<em>Neovide</em>?)
- File: <code>@g ~/Projects/tklr-uv/items/tklr.db</code>
  Open the SQLite3 file using the system default agent for <code>.db</code> files. (<em>SQLPro Studio</em>?)
- File: <code>@g ~/Projects/tklr-uv/mouse_with_watch.png</code>
  Open the image file using the system default agent for <code>.png</code> files. (<em>Preview</em>?)

Maybe an event involves a zoom meeting? Add an <code>@g</code> attribute with the URL for the meeting.

[↩︎](#table-of-contents)

### 2.15. Away from your computer? Use the cloud

There are two ways in which *tklr* supports remote usage through the the <em>cloud</em>. The examples here involve the use of <em>iCloud</em>, an <em>iPhone</em> and an <em>iPhone</em> app called <em>Textastic</em>, but these are just examples and a similar setup could be made using, e.g., <em>Google Drive</em>. All that's needed is a link to the <em>tklr</em> home directory in your cloud and a plain text / code editor on your mobile device which can access the linked directory.

#### 2.15.1. To access to your schedule

With this entry in <em>config.toml</em> in your home directory:

<code>current_command = "!tklr agenda --width 46"</code>

<em>tklr</em> will automatically output the result of the <code>agenda</code> command to the file <em>current.txt</em> in your home directory, creating the file if necessary and otherwise overwriting it whenever it needs to be updated. With a link to your home directory in <em>iCloud</em>, your agenda, trimmed to 46 characters to fit comfortably on your <em>iPhone</em> screen in portrait mode, will always be available to you. The same approach could be used with <code>weeks</code>, <code>days</code> or any other <em>tklr</em> command. The application <em>Textastic</em> is ideal for displaying the monospaced output and works well with <em>iCloud</em> files.

#### 2.15.2. To record reminders

The key here is parallel file, <em>inbox.txt</em> in your home directory. Normally this file has zero length, but if you edit it using, say, <em>Textastic</em> and record one or more reminders using exacly the same format that you would use with <em>tklr</em> and being careful to leave a blank line between reminders, then the next time <em>tklr</em> checks the length of this file and notices that it is greater than zero, it will import each of the reminders, prefixing each with a <code>?</code> character so that it will be treated as a <em>draft</em> reminder until you remove the <code>?</code> prefix.  When this process finishes, the reminders are automatically removed from <em>inbox.txt</em> so that its length is restored to zero - ready for subsequent additions. When you next open <em>tklr</em>, all the drafts will be listed together on the current day of the events listing in <em>Agenda View</em> ready for you to make any edits you like to the "drafts" and remove the <code>?</code> prefixes.

## 3. Getting Started

### 3.1. Installing _tklr_

As usual with <em>python</em> applications, <em>tklr</em> can be installed in the usual way from <em>PyPI</em> using either <code>pip</code> or <code>pipx</code>. This <code>pip</code> command can be used either to install for the first time or to upgrade an existing installation:

```
pip install -U tklr-dgraham
```

With <code>pipx</code>, two different commands are needed. For the initial installation:
```
pipx install tklr-dgraham
```

To upgrade an existing installation:
```
pipx upgrade tklr-dgraham
```

### 3.2 Starting tklr for the first time

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

### 3.3. Configuration

The default settings are in _config.toml_ in your _tklr_ home directory together with detailed explanations for each setting.

[↩︎](#table-of-contents)

## 4. Using the Command Line Interface

<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>% tklr --help                              ⏱ 13:31:53
Usage: tklr [OPTIONS] COMMAND [ARGS]...

  Tklr CLI – manage your reminders from the command
  line.

Options:
  --version      Show the version and exit.
  --home TEXT    Override the Tklr workspace
                 directory (equivalent to setting
                 $TKLR_HOME).
  -v, --verbose  Enable verbose output
  --help         Show this message and exit.

Commands:
  add
  agenda   Display the current agenda: events...
  check    Check whether an entry is valid...
  days     days(start: date = today(), end:...
  details  Display the details for a reminder...
  find     Search reminders whose subject or @d...
  finish   Mark a reminder finished, providing...
  migrate  Convert ETM reminders into a Tklr...
  query    Run an advanced query and list...
  ui       Launch the Tklr Textual interface.
  weeks    weeks(start: date = today(), end:...
</code>
</pre>

<p>Here is the main <em>tklr</em> help message. All the <em>Commands</em> other than <code>ui</code> belong to the CLI.
</p>
</div>
<div style="clear:both;"></div>


<div style="overflow:auto;">
  <pre style="float:right; margin-left:20px; width:420px; background:#111; color:#ddd; padding:12px; border-radius:6px;">
<code>% tklr agenda --help                       ⏱ 13:34:29
Usage: tklr agenda [OPTIONS]

  Display the current agenda: events for the next 3
  days with drafts and notices along with tasks
  ordered by urgency.

  Examples:   tklr agenda   tklr agenda --width 60
  tklr agenda --rich

Options:
  --width INTEGER RANGE  Maximum line width (good
                         for small screens).
  --rich                 Use Rich colors/styling
                         (default output is plain).
  --ids                  Append record ids in
                         parentheses for each
                         reminder row.
  --help                 Show this message and exit.
</code>
</pre>

<p>For the help information on a particular command, enter the name of the command and then append <code>--help</code>. E.g., here is the help for the <em>agenda</em> command.
</p>
</div>
<div style="clear:both;"></div>

<div style="overflow: auto;">
  <img src="https://raw.githubusercontent.com/dagraham/tklr-dgraham/master/screenshots/agenda_rich.png"
alt="Description" style="float: right; margin-left: 20px; width: 460px; margin-bottom: 10px;">
  <p>The <code>--rich</code> option is probably the least apparent. Using it adds <em>rich</em> colors to the format of the display. Here are examples of <em>agenda</em> with and without this argument.
  </p>
</div>
<div style="clear: both;"></div>

## 5. Coming from <em>etm</em>

The basic entry format is essentially the same in *tklr* as it was in *etm*. There are a few changes to reminder types, attributes (specified with <code>@-keys</code>) and their modifiers (specified with <code>&-keys</code>) - these are documented below.

### 5.1 Datetime entry and <code>@z</code>

The attribute <code>@z</code> to specify the timezone for datetime entries in a reminder is no longer supported. The same purpose is now achieved by appending <code>z TIMEZONE</code> to the scheduled datetime attribute. E.g.,

<code>@s 9a fri z US/Pacific</code>

would indicate that "9a fri" is to be interpreted as an <em>aware</em> datetime in the "US/Pacific" timezone. Similarly <code>z none</code> would indicate that the preceeding datetime is to be interpreted as a <em>naive</em> datetime.

### 5.2. Type Changes

|    etm    |   tklr    |
| :-------: | :-------: |
|  * event  | unchanged |
|  - task   |  ~ task   |
|  ~ goal   |  ! goal   |
|  ! inbox  |  ? draft  |
| - project | ^ project |
| % journal |  % note   |



### 5.3. Attribute Changes

|     etm     |         tklr          |
| :---------: | :-------------------: |
| @b beginby  |       @n notify       |
| @c calendar |                       |
|  @i index   |        @b bin         |
|   @j job    |   @~ task (project)   |
| @k connect  |                       |
|             | @k completions (goal) |
| @l location |      @c context       |
| @n attendee |                       |
|   @t tag    |       #hashtag        |
|             |   @t target (goal)    |

### 5.4. <code>@r</code> modifier changes

|     etm      |     tklr     |
| :----------: | :----------: |
|   &h hours   |   &H hours   |
|  &n minutes  |  &M minutes  |
|  &M months   |  &m months   |
| &m monthdays | &d monthdays |

The *tklr* settings mirror standard usage in <code>strftime</code>.

### 5.5. <code>@~</code> project task/job modifier changes

The modifers used in <code>@~</code> <em>project task</em> entries are significantly changed from the <em>etm</em> <code>@j</code> <em>job</em> entries. In <em>tklr</em>, the optional <code>&r</code> <em>requires</em> modifier replaces both the <code>&i</code> <em>id</em> and the <code>&p</code> <em>prerequisite</em> modifiers. See [doghouse project](#doghouse-example) for an example of the new usage.

## 6. Developer Guide

This guide walks you through setting up a development environment for `tklr` using [`uv`](https://github.com/astral-sh/uv) and a local virtual environment. 

#### ✅ Step 1: Clone/Update the repository

This step will create a directory named _tklr-dgraham_ in your current working directory that contains a clone of the github repository for _tklr_.

```bash
git clone https://github.com/dagraham/tklr-dgraham.git
cd tklr-dgraham
```

Later, to update your local copy of **Tklr** to the latest version:

```bash
# Navigate to your project directory
cd ~/Projects/tklr-dgraham  # adjust this path as needed

# Pull the latest changes from GitHub
git pull origin master

# Reinstall in editable mode (picks up new code and dependencies)
uv pip install -e .
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

###### Install `direnv`

```bash
brew install direnv        # macOS
sudo apt install direnv    # Ubuntu/Debian
```

###### Add the shell hook to your `~/.zshrc` or `~/.bashrc`

```sh
eval "$(direnv hook zsh)"   # or bash
```

Restart your shell or run `source ~/.zshrc`.

###### In the project directory, create a `.envrc` file

```bash
echo 'export PATH="$PWD/.venv/bin:$PATH"' > .envrc
```

###### Allow it

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
