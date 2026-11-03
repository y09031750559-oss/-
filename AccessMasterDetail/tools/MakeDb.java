import com.healthmarketscience.jackcess.*;
import java.io.File;
import java.math.BigDecimal;
import java.time.LocalDateTime;

public class MakeDb {
    public static void main(String[] a) throws Exception {
        File f = new File(a[0]); f.delete();
        try (Database db = DatabaseBuilder.create(Database.FileFormat.V2000, f)) {
            db.setDateTimeType(DateTimeType.LOCAL_DATE_TIME);
            Table c = new TableBuilder("Clients")
                .addColumn(new ColumnBuilder("ID", DataType.LONG).setAutoNumber(true))
                .addColumn(new ColumnBuilder("FullName", DataType.TEXT).setLengthInUnits(100))
                .addColumn(new ColumnBuilder("Phone", DataType.TEXT).setLengthInUnits(30))
                .addColumn(new ColumnBuilder("City", DataType.TEXT).setLengthInUnits(50))
                .addIndex(new IndexBuilder(IndexBuilder.PRIMARY_KEY_NAME).addColumns("ID").setPrimaryKey())
                .toTable(db);
            Table o = new TableBuilder("Orders")
                .addColumn(new ColumnBuilder("ID", DataType.LONG).setAutoNumber(true))
                .addColumn(new ColumnBuilder("ClientID", DataType.LONG))
                .addColumn(new ColumnBuilder("OrderDate", DataType.SHORT_DATE_TIME))
                .addColumn(new ColumnBuilder("Product", DataType.TEXT).setLengthInUnits(100))
                .addColumn(new ColumnBuilder("Quantity", DataType.LONG))
                .addColumn(new ColumnBuilder("Price", DataType.MONEY))
                .addIndex(new IndexBuilder(IndexBuilder.PRIMARY_KEY_NAME).addColumns("ID").setPrimaryKey())
                .toTable(db);
            new RelationshipBuilder("Clients", "Orders").addColumns("ID", "ClientID")
                .setReferentialIntegrity().toRelationship(db);

            c.addRow(Column.AUTO_NUMBER, "Иванов Иван", "+7 900 111-11-11", "Москва");
            c.addRow(Column.AUTO_NUMBER, "Петров Пётр", "+7 900 222-22-22", "Казань");
            c.addRow(Column.AUTO_NUMBER, "Сидорова Анна", "+7 900 333-33-33", "Самара");
            o.addRow(Column.AUTO_NUMBER, 1, LocalDateTime.of(2026,10,1,0,0), "Ноутбук", 1, new BigDecimal("65000"));
            o.addRow(Column.AUTO_NUMBER, 1, LocalDateTime.of(2026,10,5,0,0), "Мышь", 2, new BigDecimal("900"));
            o.addRow(Column.AUTO_NUMBER, 2, LocalDateTime.of(2026,10,10,0,0), "Монитор", 1, new BigDecimal("18000"));
            o.addRow(Column.AUTO_NUMBER, 3, LocalDateTime.of(2026,10,12,0,0), "Клавиатура", 1, new BigDecimal("2500"));
        }
        try (Database db = DatabaseBuilder.open(f)) {
            for (String t : db.getTableNames()) { System.out.println(t); for (Row r : db.getTable(t)) System.out.println("  " + r); }
            System.out.println(db.getRelationships(db.getTable("Clients"), db.getTable("Orders")));
        }
    }
}
