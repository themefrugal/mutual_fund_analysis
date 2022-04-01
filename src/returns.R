library(rjson)
library(data.table)
library(ggplot2)
library(plotly)

source('./utils.R')

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
dt_daily_navs <- dt_navs_1
dt_weekly_navs <- get_periodic_navs(dt_navs_1, 'weekly', 2)
dt_monthly_navs <- get_periodic_navs(dt_navs_1, 'monthly', 1)

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
mf_url <- 'https://api.mfapi.in/mf/122639' #PPFAS Flexi
mf_url <- 'https://api.mfapi.in/mf/100669' #UTI Flexi
dt_navs  <- get_navs(mf_url)

dt_cagrs <- rbindlist(lapply(c(3,5,7), function(x)get_cagr(dt_navs,x)))

# MF Analysis
p <- ggplot(dt_cagrs, aes(x=cagr)) + geom_histogram()
ggplotly(p)

p <- ggplot(dt_cagrs, aes(x=cagr, color=years)) + geom_density() +
    scale_color_brewer(palette="Dark2") + theme_minimal()
ggplotly(p)
