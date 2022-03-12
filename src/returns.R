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
dt_navs <- data.frame()
columns <- c('date', 'nav')
dt_navs <- data.frame(matrix(nrow = 0, ncol = length(columns)))
colnames(dt_navs) = columns
for (i in c(1:length(json_data[[2]]))){
    dt_navs <- rbind(dt_navs, data.frame(t(unlist(json_data[[2]][[i]]))))
}
dt_navs <- data.table(dt_navs)
