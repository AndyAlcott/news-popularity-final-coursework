package com.example.news;

import java.util.List;
import java.util.Map;
import org.apache.ibatis.annotations.*;

@Mapper
public interface RecordMapper {
    @Insert("INSERT INTO prediction_record(model,features,label,probability) VALUES(#{model},#{features},#{label},#{probability})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    void insert(Map<String, Object> record);

    @Select("SELECT id,model,features,label,probability,DATE_FORMAT(created_at,'%Y-%m-%d %H:%i:%s') AS createdAt FROM prediction_record ORDER BY id DESC LIMIT 100")
    List<Map<String, Object>> list();

    @Delete("DELETE FROM prediction_record WHERE id=#{id}")
    int delete(long id);
}
