import java.io.IOException;
import java.util.StringTokenizer;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

import org.apache.avro.Schema;
import org.apache.avro.mapred.AvroKey;
import org.apache.avro.mapred.AvroValue;
import org.apache.avro.mapreduce.AvroJob;
import org.apache.avro.mapreduce.AvroKeyValueInputFormat;
import org.apache.avro.mapreduce.AvroKeyValueOutputFormat;

import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.apache.hadoop.util.GenericOptionsParser;

import org.apache.hadoop.mapreduce.lib.input.TextInputFormat;
import org.apache.hadoop.mapreduce.lib.output.TextOutputFormat;


public class PhrasesWithWeightMerged extends Configured implements Tool{


  public static class PhraseMapper extends Mapper<AvroKey<CharSequence>, AvroValue<Long>, Text, LongWritable>{
    private LongWritable weight = new LongWritable();
    public void map(AvroKey<CharSequence> key, AvroValue<Long> value, Context context) throws IOException, InterruptedException {
      weight.set(value.datum());
      context.write(new Text(key.datum().toString()), weight);
    }
  }

  public static class WeightSumCombiner extends Reducer<Text, LongWritable, Text, LongWritable> {
    private LongWritable result = new LongWritable();
    public void reduce(Text phrase, Iterable<LongWritable> weights, Context context) throws IOException, InterruptedException {
      long weightSum = 0;
      for (LongWritable weight : weights) {
        weightSum += weight.get();
      }
      result.set(weightSum);
      context.write(phrase, result);
    }
  }

  public static class WeightSumReducer extends Reducer<Text, LongWritable, AvroKey<CharSequence>, AvroValue<Long>> {
    public void reduce(Text phrase, Iterable<LongWritable> weights, Context context) throws IOException, InterruptedException {
      long weightSum = 0L;
      for (LongWritable weight : weights) {
        weightSum += weight.get();
      }
      context.write(new AvroKey<CharSequence>(phrase.toString()), new AvroValue<Long>(weightSum));
    }
  }

  public static void main(String[] args) throws Exception {
    int result = ToolRunner.run(new Configuration(), new PhrasesWithWeightMerged(), args);
    System.exit(result);
  }

  @Override
  public int run(String[] args) throws Exception {

    if (args.length != 3) {
      System.err.printf("Usage: %s [generic options] <input> <output> <unused>\n", getClass().getName());
      ToolRunner.printGenericCommandUsage(System.err);
      System.exit(2);
    }

    Path inPath = new Path(args[0]);
    Path outPath = new Path(args[1]);
    Integer baseWeight = Integer.valueOf(args[2]);
    
    Job job = Job.getInstance(getConf(), "Phrases With Weight Merged");
    job.setJarByClass(PhrasesWithWeightMerged.class);

    job.setInputFormatClass(AvroKeyValueInputFormat.class); 
    AvroJob.setInputKeySchema(job, Schema.create(Schema.Type.STRING));
    AvroJob.setInputValueSchema(job, Schema.create(Schema.Type.LONG));
    job.setOutputFormatClass(AvroKeyValueOutputFormat.class);
    AvroJob.setOutputKeySchema(job, Schema.create(Schema.Type.STRING));
    AvroJob.setOutputValueSchema(job, Schema.create(Schema.Type.LONG));

    job.setMapperClass(PhraseMapper.class);
    job.setCombinerClass(WeightSumCombiner.class);
    job.setReducerClass(WeightSumReducer.class);

    job.setMapOutputKeyClass(Text.class);
    job.setMapOutputValueClass(LongWritable.class);

    FileInputFormat.setInputPaths(job, inPath);
    FileOutputFormat.setOutputPath(job, outPath);

    return job.waitForCompletion(true) ? 0 : 1;
  }
}