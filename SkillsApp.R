
library(shiny)
library(readxl)
library(dplyr)
library(stringr)
library(tidyr)
library(plotly)

# ---- Constants ----
fixed_categories <- c(
  "analytical", "collaboration", "interaction / ux", "management",
  "operational", "personal / soft", "technical"
)

cat_map <- list(
  "technical" = "technical", "operational" = "operational", "analytical" = "analytical",
  "collaboration" = "collaboration", "management" = "management",
  "soft" = "personal / soft", "personal/soft" = "personal / soft", "personal / soft" = "personal / soft",
  "interaction/ux" = "interaction / ux", "interaction / ux" = "interaction / ux"
)

color_map <- c("AS-IS" = "#EF553B", "TO-BE" = "#636EFA")

normalize_string <- function(s) {
  tolower(trimws(s))
}

normalize_role <- function(s) {
  gsub("[ _]", "", tolower(trimws(s)))
}

pretty_category <- function(cat) {
  tools::toTitleCase(cat)
}

ui <- fluidPage(
  titlePanel("Confronto Skills: As-Is vs To-Be"),
  sidebarLayout(
    sidebarPanel(
      fileInput("file", "Carica file Excel (.xlsx)", accept = ".xlsx"),
      uiOutput("role_inputs"),
      checkboxGroupInput("chart_types", "Visualizza grafici:",
                         choices = c("Radar", "Barre", "Bolle"),
                         selected = c("Radar", "Barre"))
    ),
    mainPanel(
      conditionalPanel("input.chart_types.includes('Radar')", plotlyOutput("radar_chart")),
      conditionalPanel("input.chart_types.includes('Barre')", plotlyOutput("bar_chart")),
      conditionalPanel("input.chart_types.includes('Bolle')", plotlyOutput("bubble_chart")),
      uiOutput("skill_details")
    )
  )
)

server <- function(input, output, session) {
  data <- reactive({
    req(input$file)
    tryCatch({
      list(
        tobe = readxl::read_excel(input$file$datapath, sheet = "Skills To Be") %>%
          rename_all(tolower) %>%
          filter(!is.na(skill)),
        asis = readxl::read_excel(input$file$datapath, sheet = "Skills As Is") %>%
          rename_all(tolower) %>%
          filter(!is.na(skill))
      )
    }, error = function(e) {
      showNotification("Errore nel caricamento del file", type = "error")
      NULL
    })
  })

  output$role_inputs <- renderUI({
    req(data())
    roles_asis <- unique(data()$asis$`role as is`)
    roles_tobe <- unique(data()$tobe$role)

    tagList(
      selectInput("asis_role", "Ruolo AS-IS", choices = roles_asis),
      selectInput("tobe_role", "Ruolo TO-BE", choices = roles_tobe)
    )
  })

  selected_data <- reactive({
    req(input$asis_role, input$tobe_role, data())

    df_asis <- data()$asis %>%
      mutate(
        cat_norm = sapply(normalize_string(`skill category`), function(x) cat_map[[x]]),
        role_clean = normalize_role(`role as is`)
      )
    df_tobe <- data()$tobe %>%
      mutate(
        cat_norm = sapply(normalize_string(`skill category`), function(x) cat_map[[x]]),
        role_clean = normalize_role(role)
      )

    sel_asis <- normalize_role(input$asis_role)
    sel_tobe <- normalize_role(input$tobe_role)

    list(
      subset_asis = df_asis %>% filter(role_clean == sel_asis),
      subset_tobe = df_tobe %>% filter(role_clean == sel_tobe)
    )
  })

  prepare_chart_data <- reactive({
    req(selected_data())

    df_asis <- selected_data()$subset_asis
    df_tobe <- selected_data()$subset_tobe

    counts_asis <- df_asis %>% count(cat_norm)
    counts_tobe <- df_tobe %>% count(cat_norm)

    categories <- fixed_categories
    values_asis <- sapply(categories, function(cat) sum(counts_asis$n[counts_asis$cat_norm == cat], na.rm = TRUE))
    values_tobe <- sapply(categories, function(cat) sum(counts_tobe$n[counts_tobe$cat_norm == cat], na.rm = TRUE))

    list(
      categories = categories,
      values_asis = values_asis,
      values_tobe = values_tobe,
      df_long = data.frame(
        Categoria = rep(sapply(categories, pretty_category), 2),
        Valore = c(values_asis, values_tobe),
        Tipo = rep(c("AS-IS", "TO-BE"), each = length(categories))
      )
    )
  })

  output$radar_chart <- renderPlotly({
    req("Radar" %in% input$chart_types, prepare_chart_data())
    p <- prepare_chart_data()
    plot_ly(type = 'scatterpolar', mode = 'lines+markers') %>%
      add_trace(
        r = c(p$values_asis, p$values_asis[1]),
        theta = c(sapply(p$categories, pretty_category), pretty_category(p$categories[1])),
        fill = 'toself',
        name = paste("AS-IS:", input$asis_role),
        line = list(color = color_map["AS-IS"])
      ) %>%
      add_trace(
        r = c(p$values_tobe, p$values_tobe[1]),
        theta = c(sapply(p$categories, pretty_category), pretty_category(p$categories[1])),
        fill = 'toself',
        name = paste("TO-BE:", input$tobe_role),
        line = list(color = color_map["TO-BE"])
      ) %>%
      layout(polar = list(radialaxis = list(visible = TRUE)), showlegend = TRUE)
  })

  output$bar_chart <- renderPlotly({
    req("Barre" %in% input$chart_types, prepare_chart_data())
    p <- prepare_chart_data()
    plot_ly(
      p$df_long, x = ~Categoria, y = ~Valore, color = ~Tipo, type = 'bar',
      colors = color_map, text = ~Valore, textposition = 'auto'
    ) %>%
      layout(barmode = "group")
  })

  output$bubble_chart <- renderPlotly({
    req("Bolle" %in% input$chart_types, prepare_chart_data())
    p <- prepare_chart_data()
    df_bubble <- p$df_long %>% filter(Valore > 0)
    plot_ly(
      df_bubble, x = ~Categoria, y = ~Tipo, size = ~Valore, color = ~Tipo,
      type = 'scatter', mode = 'markers', text = ~Valore,
      sizes = c(10, 60), marker = list(sizemode = 'diameter'),
      colors = color_map
    )
  })

  output$skill_details <- renderUI({
    req(selected_data())
    cat_selected <- fixed_categories[1]

    df_asis <- selected_data()$subset_asis
    df_tobe <- selected_data()$subset_tobe

    asis_skills <- df_asis %>% filter(cat_norm == cat_selected) %>% pull(skill)
    tobe_skills <- df_tobe %>% filter(cat_norm == cat_selected) %>% pull(skill)

    delta <- length(tobe_skills) - length(asis_skills)

    tagList(
      h4(paste("Dettaglio categoria:", pretty_category(cat_selected))),
      h5(sprintf("AS-IS (%d)", length(asis_skills))),
      if (length(asis_skills)) HTML(paste("<ul>", paste0("<li>", asis_skills, "</li>", collapse=""), "</ul>")),
      h5(sprintf("TO-BE (%d)", length(tobe_skills))),
      if (length(tobe_skills)) HTML(paste("<ul>", paste0("<li>", tobe_skills, "</li>", collapse=""), "</ul>")),
      if (delta > 0) strong(paste("Gap: +", delta, "(Skill aggiunte)")),
      if (delta < 0) strong(paste("Gap:", delta, "(Skill perse)")),
      if (delta == 0) strong("Gap: 0 (Invariato)")
    )
  })
}

shinyApp(ui, server)
