# download nav info from mfapi.in
library(rjson)
library(data.table)
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
