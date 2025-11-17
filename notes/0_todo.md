# Todo

- [x] Lists
- [x] Replace the _tags_ column in record with a _flags_ column. For these `@`-keys: a)lert, g)oto, o)ffset or r)epeat, append the corresponding 𝕒, 𝕘, 𝕠 or 𝕣 character as a "flag" if the item contains the key. When displaying the subject of a reminder, automatically append the join of the relevant flags.
- [x] Remove `@t` tags in favor of using hash tags (# followed immediately by letters and/or numbers - no spaces) in subject and details.
- [x] Add a (hash) Tag view. Regex query for hash tags in either subject or details with the results grouped by and listed by matching hash tag.
- [x] Implement do_g
- [x] Implement OpenWithDefault
- [ ] Check direct entry
    - [ ] Check adding @f directly to all possible tasks
    - [ ] Check adding @+ directly to @s only and @r with and without prior @+ entries
    - [ ] Check adding @- directly to @s only and @r with and without prior @- and @+ entries
    - [ ] Check adding @s directly to reminders without an @s entry
- [ ] Modify view action_do_finish to add the @f entry and let item do the rest
- [ ] Modify view action_do_schedule_new to add the @+ entry and let item do the rest
- [ ] Modify view action_do_skip_instance to add the @+ entry and let item do the rest
- [ ] Modify view action_do_reschedule_new to a ,dd the @+ entry and let item do the rest




## Notes on Tests

- @f 
    - Weeks updated but not Agenda after task selected in Agenda view and @f added in editing 
    - Weeks updated but not Find or Agenda after task selected in Find view and @f added in editing 
    - Multiple jobs selected in Weeks, edited and several jobs finished at once. Refreshed in Weeks AND Agenda  
    - Do over, selected in Agenda, finished in edit. Refreshed in Agenda and Weeks 
    - All day, selected and finished in Agenda. Not refreshed in Agenda but was refreshed in Weeks.
    - All day, selected and finished in Weeks. Refreshed in Weeks but not refreshed in Agenda.
    - After restart, refreshed everywhere
- @s, @+
    - @s selected and changed in Weeks, refreshed in Weeks AND Agenda
    - @+ selected and added in Agenda, refreshed in both 
    - Changed task subject in Weeks, refreshed in both


