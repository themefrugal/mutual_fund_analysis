# download nav info from mfapi.in
library(rjson)
library(data.table)
library(ggplot2)
library(plotly)

mf_url <- 'https://api.mfapi.in/mf/122639'
# json_file <- './temp.json'
# download.file(mf_url, temp_file)
# json_data <- fromJSON(paste(readLines(json_file), collapse=""))

# Directly using readLines on the URL
json_data <- fromJSON(paste(readLines(mf_url), collapse=""))
# MF Info
dt_mf_info <- data.table(t(data.frame(unlist(json_data[[1]]))))
# MF NAVs
dt_navs <- data.table(do.call(rbind.data.frame, json_data[[2]]))

mf_list_url <- 'https://api.mfapi.in/mf'
mf_list <- fromJSON(paste(readLines(mf_list_url), collapse=""))
# MF List
dt_mfs <- data.table(do.call(rbind.data.frame, mf_list))

dt_navs[, date := as.Date(date, format="%d-%m-%Y")]
dt_navs[, nav := as.numeric(nav)]
dt_navs <- dt_navs[order(date)]

# Fill in for all dates
all_dates <- seq.Date(min(dt_navs$date), max(dt_navs$date), by=1)
dt_all_dates <- data.table(all_dates)
names(dt_all_dates) <- 'date'
dt_navs <- merge(dt_all_dates, dt_navs, by='date', all.x=TRUE)
# Get the next observed value carried backward for missing days ("nocb")
dt_navs$nav <- nafill(dt_navs$nav, type='nocb')

day_fn <- function(period){
    fn_list <- list("weekly" = wday, "monthly" = mday, "yearly" = yday)
    return (fn_list[[period]])
}

get_periodic_navs <- function(dt_navs, period='weekly', ord_num=1){
    dt_navs[, day := day_fn(period)(date)]
    dt_period_navs <- dt_navs[day == ord_num]
    dt_navs[, day := NULL]
    dt_period_navs[, day := NULL]
    return(dt_period_navs)
}

# dt_navs[, nav_diff := nav - shift(nav)]
# dt_navs[, date_diff := as.numeric(date - shift(date))]
dt_daily_navs <- dt_navs
dt_daily_navs[, returns := nav / shift(nav) - 1]

dt_weekly_navs <- get_periodic_navs(dt_navs, 'weekly', 2)
dt_weekly_navs[, returns := nav / shift(nav) - 1]

p <- ggplot(dt_daily_navs, aes(x=returns)) + geom_histogram()
ggplotly(p)

p <- ggplot(dt_daily_navs, aes(x=date, y=nav)) + geom_line() + scale_y_log10()
ggplotly(p)

# Rebasing based on a specific date
from_date <- '2018-08-28'
dt_cumulative <- dt_daily_navs[date >= from_date]
dt_cumulative[, returns := nav / shift(nav)]
dt_cumulative$returns[1] <- 1
dt_cumulative[, cum_returns := cumprod(returns)]

p <- ggplot(dt_cumulative, aes(x=date, y=cum_returns)) + geom_line() + scale_y_log10()
ggplotly(p)
