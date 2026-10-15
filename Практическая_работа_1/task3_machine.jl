# Задача 3. "Планирование выпуска на станке"
# x - число деталей "X" (шт.), y - число деталей "Y" (шт.)
# Система неравенств:
#   2x + 4y ≤ 160      (время работы станка не более 160 ч)
#   y ≥ 20             (по контракту не менее 20 деталей "Y")
#   x ≥ 0              (x, y - целые числа)
# Целевая функция (прибыль):  P(x, y) = 50x + 80y → max

# Подключаем библиотеку Plots для построения графиков
using Plots

# Целевая функция - прибыль за месяц
P(x, y) = 50x + 80y

# Перебираем все целые планы и ищем план с наибольшей прибылью
function find_best_plan()
    best_x, best_y, best_p = 0, 0, 0
    for x in 0:80, y in 20:40
        if 2x + 4y <= 160 && P(x, y) > best_p
            best_x, best_y, best_p = x, y, P(x, y)
        end
    end
    return best_x, best_y, best_p
end

function plot_machine_problem(x_opt, y_opt, p_max)
    # Выражаем y из граничного уравнения 2x + 4y = 160
    y_time(x) = (160 - 2x) / 4

    # Диапазон значений x от 0 до 90 шт. с шагом 0.5
    x_range = 0:0.5:90

    # Граница по времени работы станка
    plot(x_range, y_time.(x_range),
         linewidth=2,
         title="Допустимые месячные планы выпуска",
         xlabel="Детали \"X\" x (шт.)",
         ylabel="Детали \"Y\" y (шт.)",
         label="2x + 4y = 160",
         legend=:topright,
         xlims=(0, 90), ylims=(0, 60))

    # Граница по контракту
    hline!([20], linewidth=2, label="y = 20")

    # Закрашиваем область допустимых планов (треугольник)
    plot!(Shape([0, 40, 0], [20, 20, 40]), fillcolor=:green, fillalpha=0.3,
          linecolor=:green, label="Допустимая область")

    # Линия уровня целевой функции, проходящая через оптимум
    plot!(x_range, (p_max .- 50 .* x_range) ./ 80,
          linestyle=:dash, linewidth=2, color=:purple,
          label="50x + 80y = $p_max")

    # Отмечаем оптимальный план
    scatter!([x_opt], [y_opt], color=:red, markersize=6,
             label="Максимум: ($x_opt; $y_opt)")

    return plot!()
end

x_opt, y_opt, p_max = find_best_plan()

println("Задача 3 - Планирование выпуска на станке:")
println("Система неравенств: 2x + 4y ≤ 160,  y ≥ 20,  x ≥ 0")
println("Целевая функция: P = 50x + 80y → max")
println("Оптимальный план: x = $x_opt шт., y = $y_opt шт.")
println("Загрузка станка = $(2x_opt + 4y_opt) ч")
println("Максимальная прибыль = $p_max руб.")

# Рисуем график
plot_machine_problem(x_opt, y_opt, p_max)
