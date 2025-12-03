- [ ] @m mask
- [ ] Tree view for Help?
- [ ] comma,h to see a history of completions for a repeating task
- [ ] Migration in main?
- [ ] Bin management?
- [ ] Query view
- [ ] Row_tagger for CLI
- [ ] Hijack / search
- [ ] Goal using @o 3/w = 2d8h


## Goal
- itemtype: !
- requires @s and @o
- @o takes the specific format @o NUM / PERIOD. E.g., `@o 3/w`, would set a goal of 3 completions per week.
- Starting from @s START, the goal would be to complete the goal NUM times during the INTERVAL from START to START+PERIOD.
- Initially REMAINING = NUM
- When a completion is recorded during INTERVAL, REMAINING -= 1
- Goal success or failure for INTERVAL
    - If enough completions are recorded for REMAINING to become zero during INTERVAL, then the goal was successfully achieved
    - On the other hand, if the current time reaches START+PERIOD with REMAINING > 0, then the goal was not achieved 
    - in either case, `@s = START+PERIOD`, and REMAINING = NUM. E.g., if originally `@s = Mon, Dec 1 2025` and `@o = 3/w` then `@s = Mon, Dec 8 2025` and `REMAINING = 3`.
-  Record keeping
   -  If the goal is achived for period beginning with START, the a `1` is recorded for that goal and START.
   -  If the goal is not achieved with `DONE < NUM` completed during INTERVAL, then `DONE/NUM < 1` is recorded.
   -  The goal history is thus a sequence of rational numbers between 0 and 1.
-  Status
   -  At any moment, NOW, during INTERVAL, suppose `REMAINING` instances have not yet been completed and that `TIME_LEFT = START+PERIOD - NOW` is the time remaining to complete `REMAINING`. At the beginning of the period, `PERIOD/NUM` gave the implicit rate at which completions needed to occur for success. At the current moment, `NOW`, `TIME_LEFT/REMAINING` gives the implicit rate at which completions need to occur for success. From this perspective, `TIME_LEFT/REMAINING == PERIOD/NUM` corresponds to "being precisely on schedule" for success.  Rearranging `TIME_LEFT/PERIOD == REMAINING/NUM` or `(TIME_LEFT * NUM) / (PERIOD * REMAINING) == 1` . If we let `STATUS = (TIME_LEFT * NUM) / (PERIOD * REMAINING)`, then `STATUS = 1` is on target, `STATUS > 1` is ahead of schedule and `STATUS < 1` is behind schedule. 
-  

```
   ! interval training @s 2025-12-01 @o 3/w 
```

At 8am on Wednesay with 4d16h remaining in the week and 1 of the 3 instances completed, this goal would be displayed in Goal View as
```
   ! 1 2/3 4d16h interval training
```
where "1" is the current *priority* of the goal, "2/3" is the fraction of the goal not yet completed and "4d16h" is the time remaining for completion. Goals are sorted in this view by their *priority*. 

How is *priority* determined? Suppose `i_g` is the number of instances specified in the goal and `t_g` is the period specified for their completion. In the example, `i_g = 3` and `t_g = 1w`. Further suppose that at a particular moment, `i_r` is the number of instances remaining unfinished and `t_r` is the time remaining in the period for their completion. Initially, the goal is `i_g/t_g`. At the moment being considered the goal for the remaining period is `i_r/t_r`. Note that both ratios have the units "completions per unit of time". E.g., `3/w = 1/2d8h` 

    - `i_r/t_r > i_g/t_g`: the needed rate of completion has increased  - behind schedule
    - `i_r/t_r = i_g/t_g`: the needed rate of completion is unchanged - on schedule
    - `i_r/t_r < i_g/t_g`: the needed rate of completion has decreased - ahead of schedule 

Equivalently, if `priority = (i_r * t_g) / (i_g * t_r)`:

    - `priority > 1`: the needed rate of completion has increased  - behind schedule
    - `priority = 1`: the needed rate of completion is unchanged - on schedule
    - `priority < 1`: the needed rate of completion has decreased - ahead of schedule 




At the beginning of the week, exactly 1 week remains to complete the 3 instances specified in the goal. 

This means that completing an instance every `w/3 = 2d8h` would result in completing all 3 instances precisely at the end of the week. Now suppose at a given moment in the week, `t_r` denotes the time remaining in the week and `i_r` denotes the number of incomplete instances remaining. At this moment, `i_r/t_r` represents the implied goal for the remaining period. If `t_r/i_r < w/3`, it would mean that progress toward the 