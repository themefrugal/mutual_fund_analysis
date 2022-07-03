library(shiny)
library(plotly)
navbarPage(
    title = 'Mutual Fund Analysis',
    tabPanel('Dashboard',
        fluidPage(
            sidebarPanel(
                tags$style(type="text/css",
                    ".shiny-output-error { visibility: hidden; }",
                    ".shiny-output-error:before { visibility: hidden; }"
                ),
                selectizeInput("mf_name", "Mutual Fund:", choices=c())
            ),
            mainPanel(
                tabsetPanel(
                    tabPanel('NAV',
                        h4('NAV:'),
                        fluidRow(column(6, DT::dataTableOutput('table_nav'))),
                        h4('NAV Charting:'),
                        checkboxInput('nav_log_y', 'Log Y-Axis', TRUE),
                        plotlyOutput('plot_nav'),
                        h4('Cumulative Return:'),
                        fluidRow(
                            column(6, dateInput('start_date', 'Plot From:', value='2015-01-01')),
                            column(6, checkboxInput('cumr_log_y', 'Log Y-Axis', TRUE))
                        ),
                       selectizeInput("mf_name_cumr", "Add Fund:", choices=c(), multiple=TRUE),
                       plotlyOutput('plot_cumr')
                    ),
                    tabPanel('CAGR',
                        h4('CAGR:'),
                        fluidRow(column(6, DT::dataTableOutput('table_cagr'))),
                        h4('CAGR Summary:'),
                        fluidRow(column(12, DT::dataTableOutput('table_cagr_desc'))),
                        h4('Min and Max across Years:'),
                        plotlyOutput('plot_eq_yld_curve'),
                        fluidRow(column(12, tableOutput('table_cagr_desc_long'))),
                        h4('CAGR Frequency Analysis:'),
                        plotlyOutput('plot_density'),
                        h4('CAGR Histogram Analysis:'),
                        selectInput("year_hist", "Year:", choices=c(1:10)),
                        plotlyOutput('plot_hist')
                    ),
                    tabPanel('Rolling Returns',
                        h4('Rolling Returns Analysis:'),
                        plotlyOutput('plot_rolling'),
                        h4('Comparative Rolling Return:'),
                        selectizeInput("mf_name_comprr", "Add Fund:", choices=c(), multiple=TRUE),
                        selectInput("year_cagr", "Year:", choices=c(1:10)),
                        plotlyOutput('plot_comparative_roll')
                    )
                )
            )
        )
    )
)