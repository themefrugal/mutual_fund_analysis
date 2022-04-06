

get_cagr <- function(dt_navs, num_years=1){
    dt_navs[, prev_nav := shift(nav, 365*num_years)]
    dt_cagr <- na.omit(dt_navs)
    dt_cagr[, returns := nav/prev_nav - 1]
    dt_cagr[, cagr := 100 * ((1 + returns) ^ (1/num_years) - 1)]
    dt_cagr[, years := as.factor(num_years)]
    dt_cagr <- dt_cagr[, c('date', 'years', 'cagr')]
    dt_navs[, prev_nav := NULL]     # Remove the extra column added in dt_navs
    return (dt_cagr)
}

get_cagr_desc <- function(dt_cagr){
    dt_desc <- dt_cagr[, list(
            min=min(cagr, na.rm=TRUE),
            p25=quantile(cagr, na.rm=TRUE)[2],
            median=median(cagr, na.rm=TRUE),
            mean=mean(cagr, na.rm=TRUE),
            p75=quantile(cagr, na.rm=TRUE)[4],
            max=max(cagr, na.rm=TRUE)
        ),
        by=c('years')
    ]
    return (dt_desc)
}

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

get_navs <- function(scheme_code){
    mf_url <- paste0('https://api.mfapi.in/mf/', scheme_code)
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
    dt_navs <- dt_navs[nav != 0]
    return(dt_navs)
}

first_upper <- function(sx){
    return(paste0(toupper(substring(sx, 1,1)), substring(sx, 2)))
}

prune_left <- function(sx){
    return(gsub('^[^A-Za-z]+([A-Za-z])', '\\1', sx))
}

remove_extra_space <- function(sx){
    return(gsub('\\s+', ' ', sx))
}
