# AccessMasterDetail — главная и подчинённая форма (C# WinForms + Access)

## Что внутри
- **База Access** `Shop.accdb` — создаётся автоматически при первом запуске рядом с exe:
  - `Clients` (ID, FullName, Phone, City) — главная таблица;
  - `Orders` (ID, ClientID → Clients.ID, OrderDate, Product, Quantity, Price) — подчинённая.
- **MainForm** — главная форма: таблица клиентов + встроенная таблица заказов выбранного клиента.
- **OrdersForm** — подчинённая форма (кнопка «Открыть подчинённую форму» или двойной клик по клиенту):
  показывает заказы текущего клиента, листание клиентов, добавление/удаление заказов, итоговая сумма.
- Связь форм — через `DataRelation` + `BindingSource` (как «главная/подчинённая форма» в Access):
  переход по клиентам в главной форме сразу меняет заказы в подчинённой.

## Файлы
| Файл | Назначение |
|---|---|
| `Db.cs` | создание базы, загрузка в DataSet, сохранение (с получением `@@IDENTITY`) |
| `MainForm.cs` | главная форма |
| `OrdersForm.cs` | подчинённая форма |
| `Grids.cs` | настройка колонок DataGridView |

## Запуск
1. Visual Studio 2022, .NET 8.
2. Установить **Microsoft Access Database Engine** (2016 Redistributable), если нет Office.
3. Разрядность: в `.csproj` стоит `PlatformTarget = x64`. Если Office/Engine 32-битный — поменять на `x86`.
4. Открыть `AccessMasterDetail.csproj` → F5.

Чтобы использовать свою базу — положите `Shop.accdb` рядом с exe (таблицы с теми же именами полей)
или поменяйте путь в `Db.DbPath`.
