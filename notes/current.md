# click commands (using --home)

## defaults in `config.toml`

`current = [weeks:int, width: int, auto: bool]`

## click commands

### current.txt

```
weeks(
  start: date = today,
  end: int | date = current['weeks'],
  width: int = current['width']
)
```

Example usage:
```
tklr --home ~/tklr weeks 
```


Output current styled output containing all scheduled reminders for each week beginning with the week containing `start` and extending through the number of weeks specified or the week containing `end`.

If `current['auto'] == True`, then automatically use the output from week daily to update `current.txt` in the home directory (using the defaults for `current` from `current.toml` in the home directory.

### etm.txt

Modify `migrate_etm_to_tklr` to take a single argument specifying the *etm* directory containing the `etm.json` file to be migrated.  

```
migrate(etm_dir: str)
```

Example usage:
```
tklr --home ~/tklr migrate ~/etm 
```

If the file `etm.json` exists in the specified `etm_dir` then migrate its contents to the file `etm.txt` in the current _tklr_ home directory. After editing the contents of `etm.txt`, if desired, it can be imported into _tklr_ using `tklr --home add -f etm.txt`.
