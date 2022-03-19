# download nav info from mfapi.in
library(rjson)
library(data.table)
library(ggplot2)
library(plotly)

day_fn <- function(period){
    fn_list <- list("weekly" = wday, "monthly" = mday, "yearly" = yday)
    return (fn_list[[period]])
}

get_periodic_navs <- function(dt_navs, period='weekly', ord_num=1){
    dt_navs[, day := day_fn(period)(date)]
    dt_period_navs <- dt_navs[day == ord_num]
    dt_navs[, day := NULL]
    dt_period_navs[, day := NULL]
    dt_period_navs[, returns := nav / shift(nav) - 1]
    return(dt_period_navs)
}

# Rebasing based on a specific date
get_cumulative_returns <- function(dt_navs, from_date='2018-08-28'){
    dt_cumulative <- dt_navs[date >= from_date]
    dt_cumulative[, multiple := nav / shift(nav)]
    dt_cumulative$multiple[1] <- 1
    dt_cumulative[, cum_returns := cumprod(multiple)]
    return (dt_cumulative)
}

get_navs <- function(mf_url){
    # Directly using readLines on the URL
    json_data <- fromJSON(paste(readLines(mf_url), collapse=""))

    # MF Info
    dt_mf_info <- data.table(t(data.frame(unlist(json_data[[1]]))))

    # MF NAVs
    dt_navs <- data.table(do.call(rbind.data.frame, json_data[[2]]))
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
    return(dt_navs)
}

mf_url_1 <- 'https://api.mfapi.in/mf/122639'
dt_navs_1 <- get_navs(mf_url_1)

mf_url_2 <- 'https://api.mfapi.in/mf/122640'
dt_navs_2 <- get_navs(mf_url_2)
dt_navs <- merge(dt_navs_1, dt_navs_2, by='date')
names(dt_navs) <- c('date', 'mf1', 'mf2')

mf_list_url <- 'https://api.mfapi.in/mf'
mf_list <- fromJSON(paste(readLines(mf_list_url), collapse=""))
dt_mfs <- data.table(do.call(rbind.data.frame, mf_list))

# dt_navs[, nav_diff := nav - shift(nav)]
# dt_navs[, date_diff := as.numeric(date - shift(date))]
dt_daily_navs <- dt_navs
dt_weekly_navs <- get_periodic_navs(dt_navs, 'weekly', 2)
dt_monthly_navs <- get_periodic_navs(dt_navs, 'monthly', 1)

# Histogram
p <- ggplot(dt_monthly_navs, aes(x=returns)) + geom_histogram()
ggplotly(p)

# NAV Plot
p <- ggplot(dt_daily_navs, aes(x=date, y=nav)) + geom_line() + scale_y_log10()
ggplotly(p)

# Cumulative Return Plot
dt_cumr <- get_cumulative_returns(dt_daily_navs, '2016-02-05')
p <- ggplot(dt_cumr, aes(x=date, y=cum_returns)) + geom_line() + scale_y_log10()
ggplotly(p)

# MF Analysis
mf_url <- 'https://api.mfapi.in/mf/122639'
dt_navs  <- get_navs(mf_url)

get_cagr <- function(dt_navs, num_years=1){
    dt_navs[, prev_nav := shift(nav, 365*num_years)]
    dt_cagr <- na.omit(dt_navs)
    dt_cagr[, returns := nav/prev_nav - 1]
    dt_cagr[, cagr := (1 + returns) ^ (1/num_years) - 1]
    dt_cagr[, years := as.factor(num_years)]
    dt_cagr <- dt_cagr[, c('date', 'years', 'cagr')]
    return (dt_cagr)
}

dt_cagrs <- rbindlist(lapply(c(3,5,7), function(x)get_cagr(dt_navs,x)))

# MF Analysis
p <- ggplot(dt_cagrs, aes(x=cagr)) + geom_histogram()
ggplotly(p)

p <- ggplot(dt_cagrs, aes(x=cagr, color=years)) + geom_density() +
    scale_color_brewer(palette="Dark2") + theme_minimal()
ggplotly(p)
