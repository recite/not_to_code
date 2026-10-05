### Not to Code: Evidence From Static Code Analysis of Replication Scripts

Using replication files I downloaded [here](https://github.com/recite/softverse), I run some static code analysis using [lintr](https://lintr.r-lib.org/). 

For R files in the replication archives of AJPS articles posted to Harvard Datavaerse, the statistics are somewhat grim. 

```
> median(lint_results$style, na.rm = T)
[1] 156

> mean(lint_results$warning, na.rm = T)
[1] 5.866562

> mean(lint_results$error, na.rm = T)
[1] 0.005756149
```

## Scripts

* [Scripts](scripts/)
